"""Optional local developer Ed25519 signing helper. Never stores private key in repo by default.

keygen writes a private PEM with mode 0600 to an explicit operator path;
share only the printed public hex. The local CLI's key enrollment is NOT proof
of the true Origin's identity; out-of-band authorization is still required.
"""
import argparse,json,os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from olgm.improve import approval_message

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('keygen');a.add_argument('--private-out',required=True)
    a=sub.add_parser('sign');a.add_argument('--private',required=True)
    a.add_argument('--receipt',required=True);a.add_argument('--signature-out',required=True)
    args=parser.parse_args()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    if args.cmd=='keygen':
        if Path(args.private_out).exists():raise ValueError('refusing_to_overwrite_private_key')
        key=Ed25519PrivateKey.generate()
        pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
        fd=os.open(args.private_out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(pem)
        pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        print(json.dumps({'public_key_hex':pub,'private_key_path':args.private_out,
            'warning':'LOCAL DEV ONLY; private key must never be uploaded or shared'}))
    else:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        key=load_pem_private_key(Path(args.private).read_bytes(),password=None)
        if not isinstance(key,Ed25519PrivateKey):raise ValueError('expected_ed25519_private_key')
        receipt=json.loads(Path(args.receipt).read_text(encoding='utf-8'))
        if receipt.get('domain')!='OLGM-G06-SOURCE-MUTATION-v1':raise ValueError('bad_receipt_domain')
        sig=key.sign(approval_message(receipt)).hex()
        out=Path(args.signature_out)
        if out.exists():raise ValueError('refusing_to_overwrite_signature')
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='ascii') as f:f.write(sig+'\n')
        print(json.dumps({'status':'SIGNED','signature_file':str(out),
            'notice':'Operator must inspect proposal diff and checks before applying'}))

if __name__=='__main__':main()
