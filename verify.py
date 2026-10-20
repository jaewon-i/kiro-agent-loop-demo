import subprocess, pathlib, sys
root=pathlib.Path(__file__).resolve().parent
out=root/'.build';out.mkdir(exist_ok=True)
commands=[['javac','-d',str(out),str(root/'src/DiscountCalculator.java'),str(root/'tests/DiscountTest.java')],['java','-cp',str(out),'DiscountTest']]
for cmd in commands:
    r=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    print(r.stdout,end='',flush=True)
    if r.returncode: sys.exit(r.returncode)
