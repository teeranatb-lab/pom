"""Offline benchmark + optional real PEFT LoRA training adapter.

Training is never launched automatically. No trained model is claimed unless
train() actually returns TRAINED_WITH_ARTIFACTS with changed trainable tensors.
End-to-end T17 still requires held-out independent benchmarks and model provenance.
"""
import hashlib
import json
import os
import statistics
import time
from pathlib import Path


def sha256_file(path):
    sha=hashlib.sha256()
    with open(path,'rb') as fp:
        for chunk in iter(lambda:fp.read(1024*1024),b''):
            sha.update(chunk)
    return sha.hexdigest()


def evaluate_jsonl(eval_file,predict_fn):
    """Exact-match offline scoring on JSONL {input,expected}; caller supplies predictor."""
    if not callable(predict_fn):return {'status':'BLOCKED','reason':'predict_fn_required'}
    latencies=[];scores=[];rows=[]
    with open(eval_file,encoding='utf-8') as file:
        for line_number,line in enumerate(file,1):
            if not line.strip():continue
            item=json.loads(line)
            if 'input' not in item or 'expected' not in item:
                raise ValueError(f'bad eval item at line {line_number}')
            t0=time.perf_counter()
            output=predict_fn(item['input'])
            latencies.append((time.perf_counter()-t0)*1000)
            correct=str(output).strip()==str(item['expected']).strip()
            scores.append(correct)
            rows.append({'line':line_number,'correct':correct,
                         'input_sha256':hashlib.sha256(str(item['input']).encode()).hexdigest()})
    if not scores:return {'status':'BLOCKED','reason':'empty_eval_dataset'}
    vals=sorted(latencies)
    p95=vals[max(0, (95*len(vals)+99)//100-1)]
    return {'status':'EVALUATED','items':len(scores),'accuracy':sum(scores)/len(scores),
            'latency_ms_p50':statistics.median(latencies),'latency_ms_p95':p95,
            'eval_sha256':sha256_file(eval_file),'per_item':rows,
            'limitations':'Exact-match only; evaluate on independent holdout and audit leakage.'}


class TrainingPipeline:
    """Version-adaptive LoRA training on text JSONL; no pretrained weights bundled."""
    def __init__(self,base_model,adapter_dir='adapters'):
        self.base=base_model;self.adapter_dir=str(adapter_dir)

    def train(self,train_data_path,output_name='v1',epochs=1,lr=2e-4,
              max_length=256,target_modules=None,require_cuda=True):
        """Real Trainer path with hashes and trainable-parameter change proof.

        Dependencies: torch, transformers, peft, accelerate. Data JSONL {text:str}.
        For low resource machines use compact models and tune max_length/epochs.
        Independent held-out accuracy is NOT inferred from train loss.
        """
        try:
            import torch
            from torch.utils.data import Dataset
            from transformers import (AutoTokenizer,AutoModelForCausalLM,
                                      TrainingArguments,Trainer,default_data_collator)
            from peft import LoraConfig,get_peft_model,TaskType
        except ImportError as exc:
            return {'status':'BLOCKED','reason':f'missing_training_dependency:{exc}'}
        if require_cuda and not torch.cuda.is_available():
            return {'status':'BLOCKED','reason':'cuda_unavailable','train_started':False}
        if not os.path.isfile(train_data_path):
            return {'status':'BLOCKED','reason':'training_dataset_missing'}
        if (not output_name or '/' in output_name or '\\' in output_name or
            int(epochs)<1 or int(max_length)<32 or int(max_length)>4096 or not 0<lr<1):
            raise ValueError('unsafe training configuration')
        out=Path(self.adapter_dir)/output_name
        if out.exists() and any(out.iterdir()):
            return {'status':'BLOCKED','reason':'refuse_overwrite_existing_adapter'}
        out.mkdir(parents=True,exist_ok=True)
        samples=[]
        with open(train_data_path,encoding='utf-8') as f:
            for line in f:
                if not line.strip():continue
                data=json.loads(line)
                if not isinstance(data.get('text'),str) or not data['text'].strip():
                    raise ValueError('training item needs nonempty text')
                samples.append(data['text'])
        if len(samples)<2:raise ValueError('training dataset needs at least two records')
        tok=AutoTokenizer.from_pretrained(self.base,trust_remote_code=False)
        if tok.pad_token is None:tok.pad_token=tok.eos_token
        model=AutoModelForCausalLM.from_pretrained(self.base,trust_remote_code=False)
        model.config.use_cache=False
        config=dict(task_type=TaskType.CAUSAL_LM,r=8,lora_alpha=16,lora_dropout=0.05)
        if target_modules:config['target_modules']=list(target_modules)
        model=get_peft_model(model,LoraConfig(**config))
        if not any(p.requires_grad for p in model.parameters()):
            return {'status':'BLOCKED','reason':'no_trainable_adapter_parameters'}

        def parameter_fingerprint():
            h=hashlib.sha256()
            with torch.no_grad():
                for name,param in model.named_parameters():
                    if param.requires_grad:
                        h.update(name.encode())
                        h.update(param.detach().cpu().contiguous().numpy().tobytes())
            return h.hexdigest()

        before=parameter_fingerprint()
        class TextDataset(Dataset):
            def __len__(self):return len(samples)
            def __getitem__(self,i):
                x=tok(samples[i],truncation=True,padding='max_length',max_length=int(max_length))
                x['labels']=[tok_id if mask else -100 for tok_id,mask in zip(x['input_ids'],x['attention_mask'])]
                return x
        args=TrainingArguments(output_dir=str(out/'trainer'),num_train_epochs=int(epochs),
                               learning_rate=float(lr),per_device_train_batch_size=1,
                               gradient_accumulation_steps=2,save_strategy='no',
                               logging_steps=1,report_to='none',remove_unused_columns=False,
                               seed=42)
        trainer=Trainer(model=model,args=args,train_dataset=TextDataset(),
                        data_collator=default_data_collator)
        history=trainer.train()
        after=parameter_fingerprint()
        if before==after:
            return {'status':'FAILED','reason':'trainable_adapter_parameters_unchanged'}
        model.save_pretrained(str(out));tok.save_pretrained(str(out))
        hashes={str(p.relative_to(out)):sha256_file(p) for p in sorted(out.rglob('*')) if p.is_file()}
        from datetime import datetime,timezone
        manifest={'base_model':self.base,'dataset_sha256':sha256_file(train_data_path),
                  'adapter_path':str(out),'trainable_params_hash_before':before,
                  'trainable_params_hash_after':after,'artifact_hashes':hashes,
                  'trained_at':datetime.now(timezone.utc).isoformat(),
                  'training_loss_reported':float(history.training_loss),
                  'model_behavior_improved':'NOT_TESTED','heldout_benchmark':'NOT_TESTED',
                  'source_code_version':'0.4.0'}
        with (out/'manifest.json').open('w',encoding='utf-8') as f:
            json.dump(manifest,f,ensure_ascii=False,indent=2)
        return {'status':'TRAINED_WITH_ARTIFACTS','manifest':manifest,
                'verification':'parameters_changed_not_accuracy_proof'}

    def benchmark(self,eval_file,predict_fn):
        if not os.path.isfile(eval_file):return {'status':'BLOCKED','reason':'eval_file_missing'}
        return evaluate_jsonl(eval_file,predict_fn)
