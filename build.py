import re,json,html,urllib.request,urllib.parse,datetime,sys,os
UA={"User-Agent":"Mozilla/5.0"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read().decode('utf8','ignore')
def lines(h):
    t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S)
    t=re.sub(r'<[^>]+>','\n',t); t=html.unescape(t)
    return [l.strip() for l in t.split('\n') if l.strip()]
items={}
IMG={}
def harvest(h):
    for m in re.finditer(r'<img[^>]*>',h):
        t=m.group(0)
        a=re.search(r'alt="([^"]*)"',t)
        u=re.search(r'(https(?:%3A|:)(?:%2F|/){2}images\.thdstatic\.com[^"&\s,]*?\.(?:jpg|png|jpeg))',t)
        if a and u:
            url=urllib.parse.unquote(u.group(1)).replace('_64_','_100_').replace('_64.','_100.')
            IMG[html.unescape(a.group(1)).strip().lower().rstrip('.')]=url
def findimg(name):
    n=name.strip().lower().rstrip('.')
    if n in IMG:return IMG[n]
    for k,v in IMG.items():
        if len(k)>25 and (n.startswith(k[:30]) or k.startswith(n[:30])):return v
    return ''
ZONES=[(r'toilet|vanity|faucet|sink|shower|bath|plumb|hose|pipe|valve|water heater','Plumbing / Bath','Back-center of store, near Kitchen and Bath showrooms'),
(r'light|lamp|sconce|bulb|fan|led|spotlight|chandelier','Lighting & Fans','Middle of store, lighting aisles'),
(r'wire|outlet|surge|dimmer|switch|conduit|breaker|ups|battery backup|stripper','Electrical','Middle of store, electrical aisles'),
(r'vacuum|drill|saw|tool|milwaukee|ridgid|ryobi|one\+|glove|work light|hand truck|tripod|wrench|blade','Tools / Work Gear','Front-to-middle, power tools and hand tool aisles'),
(r'paint|spray|stain|primer|brush','Paint','Front or side of store, paint desk area'),
(r'grill|patio|garden|mower|outdoor|trimmer|pressure washer|bbq','Outdoor / Garden','Garden center or outdoor living, usually outside or at the front'),
(r'tile|floor|lumber|board|door|window|blind|shade|treatment','Building Materials / Flooring','Back of store, flooring and lumber'),
(r'storage|bag|rack|packout|shelf|organizer|moving','Storage / Organization','Middle of store, storage aisles'),
(r'heat|vent|hvac|air|filter|thermostat|cooling','Heating & Cooling','Middle-back, HVAC aisles'),
(r'headphone|speaker|smart|camera|wi-?fi|alexa','Electronics / Smart Home','Front or middle, near electrical or smart home endcaps')]
def zone(name):
    for rx,z,loc in ZONES:
        if re.search(rx,name,re.I):return z,loc
    return 'General','Ask a Home Depot associate or check the app aisle number'
def add(sku,name,retail,src,**k):
    sku=sku.replace('-','')
    d=items.setdefault(sku,{"sku":k.get('skufmt',sku),"name":name,"retail":0,"reports":0,"states":0,"fl":0,"lee":False,"fl_cities":"","last":"","sources":[]})
    if name and len(name)>len(d["name"]):d["name"]=name
    d["retail"]=max(d["retail"],retail or 0)
    for f in("reports","states","fl"):d[f]=max(d[f],k.get(f,0))
    d["lee"]=d["lee"] or k.get("lee",False)
    if k.get("cities"):d["fl_cities"]=k["cities"]
    if k.get("last") and not d["last"]:d["last"]=k["last"]
    if src not in d["sources"]:d["sources"].append(src)
LEE=re.compile(r'Fort Myers|Cape Coral|Bonita|Estero|Lehigh|Sanibel|Pine Island|Lee County',re.I)
def money(s):
    m=re.search(r'\$([\d,]+\.?\d*)',s);return float(m.group(1).replace(',','')) if m else 0
status={}
# PennyCentral
try:
    H=get("https://www.pennycentral.com/penny-list");harvest(H);L=lines(H);n=0
    for i,l in enumerate(L):
        if l=='SKU' and i+1<len(L) and re.match(r'[\d-]+$',L[i+1]):
            # name is a few lines before price lines
            j=i-1
            while j>0 and not L[j].startswith('$'):j-=1
            retail=money(L[i-1]);
            name=L[j-2] if L[j-1]=='$0.01' or True else ''
            k=j
            while k>0 and L[k]!='$0.01':k-=1
            name=L[k-1]
            blk=" ".join(L[i:i+30]);rep=re.search(r'Community (\d+) reports? (\d+) states?',blk.replace('\n',' '))
            blk2=" ".join(L[i:i+40]);fl=re.search(r'FL : (\d+)',blk2)
            seen=L[i+3] if i+3<len(L) else ''
            add(L[i+1],name,retail,"PennyCentral",reports=int(rep.group(1)) if rep else 0,states=int(rep.group(2)) if rep else 0,fl=int(fl.group(1)) if fl else 0,last=seen,skufmt=L[i+1]);n+=1
    status["PennyCentral"]=n
except Exception as e:status["PennyCentral"]="error "+str(e)
# Penny Recon FL
try:
    H=get("https://www.pennyrecon.com/state/fl/");harvest(H);L=lines(H);n=0
    for i,l in enumerate(L):
        if l.startswith('SKU ') and i+2<len(L):
            sku=l[4:]
            name=L[i-1];retail=money(" ".join(L[i+1:i+4]))
            blk=" ".join(L[i:i+14]);rep=re.search(r'(\d+) reports? (\d+) states?',blk)
            fl=re.search(r'Florida: (\d+) reports? \(([^)]*)\)',blk)
            seen=re.search(r'Last seen (\S+(?: \S+ ago)?)',blk)
            cities=fl.group(2) if fl else ''
            add(sku,name,retail,"Penny Recon",reports=int(rep.group(1)) if rep else 0,states=int(rep.group(2)) if rep else 0,fl=int(fl.group(1)) if fl else 0,lee=bool(LEE.search(cities)),cities=cities,last=seen.group(1) if seen else '',skufmt=sku);n+=1
    status["Penny Recon"]=n
except Exception as e:status["Penny Recon"]="error "+str(e)
# Penny Pinchin Mom
try:
    L=lines(get("https://pennypinchinmom.com/home-depot-penny-list/"));n=0
    for i,l in enumerate(L):
        if re.match(r'^\d[\d-]{3,}$',l) and i>0 and len(L[i-1])>12:
            add(l,L[i-1],0,"Penny Pinchin' Mom",skufmt=l);n+=1
    status["Penny Pinchin' Mom"]=n
except Exception as e:status["Penny Pinchin' Mom"]="error "+str(e)
# score
import math
for d in items.values():
    srcb=1+0.25*(len(d["sources"])-1)
    d["score"]=round((d["retail"] or 15)*math.log2(2+d["reports"])*(1+0.15*min(d["fl"],10))*(1.5 if d["lee"] else 1)*srcb,1)
for d in items.values():
    d["img"]=findimg(d["name"]);d["zone"],d["where"]=zone(d["name"])
    d["url"]="https://www.homedepot.com/s/"+d["sku"].replace("-","")
rows=sorted(items.values(),key=lambda d:-d["score"])
out={"updated":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime("%b %d, %I:%M %p ET"),"status":status,"items":rows}
prev=set()
try:prev={i["sku"] for i in json.load(open("data.json"))["items"]}
except Exception:pass
new=[i for i in rows if i["sku"] not in prev and (i["lee"] or i["score"]>=800 or i["fl"]>=3)]
json.dump(out,open("data.json","w"),indent=1)
topic=os.environ.get("NTFY_TOPIC") or "penny-radar-alston-k7q2x9"
if topic and prev and new:
    body="\n".join(f"{'[LEE] ' if i['lee'] else ''}${i['retail']:.0f} {i['name'][:60]} ({i['zone']})" for i in new[:6])
    try:
        urllib.request.urlopen(urllib.request.Request("https://ntfy.sh/"+topic,data=body.encode(),headers={"Title":f"{len(new)} new penny lead(s)","Click":"https://alstonebron.github.io/penny-radar/","Priority":"high" if any(i['lee'] for i in new) else "default"}),timeout=20)
    except Exception as e:print("ntfy fail",e)
print("new",len(new))
tpl=open("template.html").read().replace("__DATA__",json.dumps(out))
open("index.html","w").write(tpl)
print(status,len(rows))
