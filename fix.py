import re 
f=open('app/templates/home.html',encoding='utf-8').read() 
f=re.sub(r'.AI-POWERED SHOPPING PLATFORM','Beyond Shopping. An Experience.',f) 
open('app/templates/home.html','w',encoding='utf-8').write(f) 
