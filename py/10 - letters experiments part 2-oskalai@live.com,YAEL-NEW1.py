import tools, turk, csv, random
from numpy import *
import matplotlib.pyplot as plt
import Tkinter
from PIL import Image, ImageTk



def trips2M3(trips):
    n = max([max((a,b,c)) for (a,b,c,d) in trips])+1
    Mb = zeros((n,n,n),'int32')
    for (a,b,c,wid) in trips:
        Mb[a][b][c]+=1
    M = zeros((n,n,n))
    for a in range(n):
        for b in range(n):
            for c in range(n):
                if Mb[a][b][c]+Mb[a][c][b]>0:
                    M[a][b][c]=(Mb[a][b][c]-Mb[a][c][b])*1.0/(Mb[a][b][c]+Mb[a][c][b])
                else:
                    M[a][b][c] = 0.00001
    return M

def match(c,l):
    n = len(c)
    if n*5!=len(l): 
        print "* Mismatch in length"
        return False
    cd  = {}
    for i in range(n):
        r = []
        for j in range(3):
            r.append(ord(c[i][j])-97)
        r = tuple(r)
        assert r not in cd
        cd[r]=1
    for i in range(n):        
        r = []
        for j in range(3):
            r.append(int(l[5*i+j]))
        r = tuple(r)
        (u,v,w)=r
        if v<w:
            r = (u,w,v)            
        if r not in cd or cd[r]!=1:
            print "* Mismatch in answer"
            return False
        cd[r]=0
    return True
 
def results2sess(label = None,ignore_list=[]):
    label = label or turk.get_last_label()
    file = open(turk.log_root+"/"+label+".results","r")
    blah = csv.DictReader(file,delimiter='\t')
    sess = []
    for r in blah:
        wid = r['workerid']
        if wid in ignore_list:
            continue
        challenge = r['annotation'].split("_")
        li = r['Answer.res'].split("_")
        assert challenge[0]==li[0]    
        if match(challenge[1:],li[1:]):
            n = (len(li)-1)/5
            li2 = [tuple(li[5*i+1:5*i+6]) for i in range(n)]
            li3 = [((a,b,c,e,d) if d=='0' else (a,c,b,e,d)) for (a,b,c,d,e) in li2]
            sess.append([wid]+[(int(a),int(b),int(c),int(e)*0.001,d) for (a,b,c,e,d) in li3])
    file.close()
    return sess

def results2trips(label = None,ignore_list=[]):
    label = label or turk.get_last_label()
    file = open(turk.log_root+"/"+label+".results","r")
    blah = csv.DictReader(file,delimiter='\t')
    trips = []
    for r in blah:
        wid = r['workerid']
        if wid in ignore_list:
            continue
        challenge = r['annotation'].split("_")
        li = r['Answer.res'].split("_")
        assert challenge[0]==li[0]    
        if match(challenge[1:],li[1:]):
            n = (len(li)-1)/5
            li2 = [tuple(li[5*i+1:5*i+6]) for i in range(n)]
            li3 = [((a,b,c) if d=='0' else (a,c,b)) for (a,b,c,d,e) in li2]
            trips += [(int(a),int(b),int(c),wid) for (a,b,c) in li3]
    file.close()
    return trips
    
#returns a random regular bipartite graph with m nodes on left,
#n nodes on right, and degree d on the left.  If n | dm then the degree on
#the right is exactly n/(md) otherwise it's as close as possible
def reg_bipartite(m,n,d):
    x = range(n)
    random.shuffle(x)
    x=x[:(m*d)%n]
    x += range(n)*((m*d)/n)
    random.shuffle(x)
    res = [ [] for i in range(m) ]
    while x:
        a = x.pop()
        while True:
            i = random.randint(0,m)
            if a not in res[i]:
                if len(res[i])==d:
                    x.append(res[i].pop(random.randint(0,len(res[i]))))
                res[i].append(a)
                break
    return res




def decode_choose2(n,m):
    assert m<(n*(n-1))/2
    count = 0
    for i in range(n):
        for j in range(i):
            if count == m:
                return (i,j)
            count+=1

def go_10(): #actually used for 9, not warmup!
    inp = "calibrialpha"
    n = 26*13*25
    bp = reg_bipartite(5*n/50,n,50)
    inp = ""
    s = {}
    while True:
        inp +="calibrialpha"
        x = bp.pop()
        for r in x:
            a = r%26
            (b,c) = decode_choose2(26,r/26)
            inp +="_"+chr(97+a)+chr(97+b)+chr(97+c)
        if not bp:
            break
        inp+="\n"
    turk.load_external_hit(title="Which letters are most similar",
                      description="Which of two letters is most similar to a third?",
                      reward="0.20",
                      keywords="letters, similarity",
                      comment="Letters take 2 alert cheaters",
                      input = inp)



def log_likely(pos,neg,p,t):
    #actually, negative-log-likelihood.
    res = 0.0
    m = len(pos)    
    for i in range(m):
        for j in pos[i]:
            res -= log( 0.5 + t[j]*(p[i]-0.5)  ) 
        for j in neg[i]:
            res -= log( 0.5 + t[j]*(0.5-p[i]) )
    return res



#update how much they are trying, t \in [0,1] (t=0 is guessing)
#bits is the number of bits of precision in t
#essentially does a binary search for right value by checking
#sign of derivative of the log_likely as a function of t
#Since the log-likelihood is single-peaked, binary search should work
def update_t(pos,neg,p,t,bits=20):
    step = 0.5
    m = len(neg) 
    n = len(t)
    t[:]=0.5
    cum = zeros(n)
    for b in range(bits):
        cum[:]=0.0    #the derivative of log-likelihood
        for i in range(m):
            #p[i] is estimated prob. that the trip should be positive
            for j in pos[i]:
                cum[j]+=(2*p[i]-1)/(1+t[j]*(2*p[i]-1))
            for j in neg[i]:
                cum[j]+=(1-2*p[i])/(1+t[j]*(1-2*p[i]))
        step/=2
        t += step*sign(cum)
    for i in range(n):
        t[i] = min(t[i],0.99)

def update_p(pos,neg,p,t,bits=20):
    m = len(neg) 
    n = len(t)
    for i in range(m):
        tempp = 0.5
        step = 0.5
        for b in range(bits):
            cum=0.0    #the derivative of log-likelihood
            for j in pos[i]:
                cum+=t[j]/(1+t[j]*(2*tempp-1))
            for j in neg[i]:
                cum-=t[j]/(1+t[j]*(1-2*tempp))
            step/=2
            tempp += step*sign(cum)
        p[i] = max(min(tempp,0.999),0.001)


def score_trips2(trips):
    #first make wid_table
    wids = []
    wid_table = {}
    for (x,y,z,wid) in trips:
        if wid not in wid_table:
            wid_table[wid]=len(wids)
            wids.append(wid)
    n = len(wids)
    #now make trip_table
    trips_list = []
    trip_table = {}
    for (x,y,z,wid) in trips:
        if (x,y,z) not in trip_table and (x,z,y) not in trip_table:
            trip_table[(x,y,z)]=len(trips_list)
            trips_list.append((x,y,z))
    m = len(trips_list)
    #now make list of pos and neg
    pos = []
    neg = []
    for i in range(m):
        pos.append([])
        neg.append([])
    for (x,y,z,wid) in trips:
        j = wid_table[wid]
        if (x,y,z) in trip_table:
            i = trip_table[(x,y,z)]
            pos[i].append(j)
        else:
            i = trip_table[(x,z,y)]
            neg[i].append(j)
    
    
    t = zeros(n)
    t[:] = 0.5 #guess each person is 0.5 trying initially
    p = zeros(m)
    p[:] = 0.5 #guess each question has 50/50 answer initially
    c = log_likely(pos,neg,p,t)
    for i in range(15):
        tot = 0.
        count = 0
        for (x,y,z) in trip_table:
            if y==x:
                tot += 1-p[trip_table[(x,y,z)]]
                count+=1
            if z==x:
                tot += p[trip_table[(x,y,z)]]
                count+=1
        print "*", tot/count

        print c
        update_p(pos,neg,p,t)
        for j in range(m):
            (x,y,z) = trips_list[j]
            if x==y:
                p[j]=1.0
            if x==z:
                p[j]=0.0
            
        print "\t\t",log_likely(pos,neg,p,t)
        update_t(pos,neg,p,t)
        cc = log_likely(pos,neg,p,t)
        if cc>c:
            print "SHOOT!",i,cc-c
        c = cc

    c1 = 0
    c2 = 0
    for (u,v,w,wid) in trips:
        if u==w:
            c1+=t[wid_table[wid]]
        if u==v:
            c2+=t[wid_table[wid]]
        assert v!=w
    print c1*1./(c1+c2) 
    plt.clf()
    plt.hist(t)
    plt.show()
    M = zeros((n,n,n))
    for j in range(m):
        (x,y,z) = trips_list[j]
        M[x][y][z]=p[j]*2-1
        M[x][z][y]=1-2*p[j]
        
    return (wids,t,M)
            




def compression_score(pos,neg,p):
    #log prob given params
    res = 0.0
    m = len(pos)
    assert m == len(neg) # distinct trips
    for i in range(m):
        res -= log( 0.5*(prod( [ (1+p[j])/2 for j in pos[i] ] ) * prod( [ (1-p[j])/2 for j in neg[i] ] ) + prod( [ (1+p[j])/2 for j in neg[i] ] ) * prod( [ (1-p[j])/2 for j in pos[i] ] )) )
    return res
    
def update_params(pos,neg,p):
    m = len(neg)
    n = len(p)
    acc = zeros(n)
    t = zeros(n)
    for i in range(m):
        a = prod( [ (1+p[j])/2 for j in pos[i] ] ) * prod( [ (1-p[j])/2 for j in neg[i] ] ) 
        b = prod( [ (1+p[j])/2 for j in neg[i] ] ) * prod( [ (1-p[j])/2 for j in pos[i] ] )
        g=a/(a+b)
        #estimate g is the posterior probability that the trip should be positive
        for j in pos[i]:
            t[j]+=1
            acc[j]+=g
        for j in neg[i]:
            t[j]+=1
            acc[j]+=1-g
    for j in range(n):
        ax = acc[j]/t[j]
        p[j]=2*ax-1
        if p[j]<0.:
            p[j]=0.
        if p[j]>1.:
            p[j]=1.
    return compression_score(pos,neg,p)

def score_trips(trips):
    #first make wid_table
    wids = []
    wid_table = {}
    for (x,y,z,wid) in trips:
        if wid not in wid_table:
            wid_table[wid]=len(wids)
            wids.append(wid)
    n = len(wids)
    #now make trip_table
    trips_list = []
    trip_table = {}
    for (x,y,z,wid) in trips:
        if (x,y,z) not in trip_table and (x,z,y) not in trip_table:
            trip_table[(x,y,z)]=len(trips_list)
            trips_list.append((x,y,z))
    m = len(trips_list)
    #now make list of pos and neg
    pos = []
    neg = []
    for i in range(m):
        pos.append([])
        neg.append([])
    for (x,y,z,wid) in trips:
        j = wid_table[wid]
        if (x,y,z) in trip_table:
            i = trip_table[(x,y,z)]
            pos[i].append(j)
        else:
            i = trip_table[(x,z,y)]
            neg[i].append(j)
    
    
    p = [0.5]*n
    c = compression_score(pos,neg,p)
    for i in range(15):
        print c
        cc = update_params(pos,neg,p)
        if cc>c:
            print "SHOOT!",i,cc-c
        c = cc
    c1 = 0
    c2 = 0
    for (u,v,w,wid) in trips:
        if u==w:
            c1+=p[wid_table[wid]]
        if u==v:
            c2+=p[wid_table[wid]]
        assert v!=w
    print c1*1./(c1+c2)    
    plt.clf()
    plt.hist(p)
    plt.show()

    return p
            

def find_overworkers(trips,n=35):
    counts = {}
    for (a,b,c,wid) in trips:
        if wid in counts:
            counts[wid]+=1
        else:
            counts[wid]=1
    bads = []
    for wid in counts:
        if counts[wid]>(50*n):
            bads.append(wid)
    return bads



hoho = []
trips1 = results2trips(ignore_list = hoho)
trips0 = results2trips("9")
trips = trips0+trips1


c1 = 0
c2 = 0
for (u,v,w,wid) in trips: 
    if u==w:
        c1+=1
    if u==v:
        c2+=1
    assert v!=w
print c1*1./(c1+c2)

(wids,t,MM)=score_trips2(trips)



#sess = results2sess(ignore_list=hoho)
#times = zeros(50)
#times2 = zeros(50)
#count = 0
#for s in sess:
#    wid = s[0]
#    times+=[e for (a,b,c,e,f) in s[1:]]
#    times2+=[e*e for (a,b,c,e,f) in s[1:]]
#    count+=1
#times/=count
#times2/=count
#times2 = sqrt(times2-times*times)
#n = len(wids)
#
#means = zeros(n)
#stds = zeros(n)
#counts = zeros(n)
#for s in sess:
#    wid = s[0]
#    i = wids.index(wid)
#    #average of the 40 shortest times
#    means[i] += mean(sort([e for (a,b,c,e,f) in s[1:]])[:40]) 
#    counts[i] +=1
#
#means/=counts

for i in range(n):
     if t[i]>0.99 and t[i]<0.99: print t[i]
 

counts = zeros(n)

scores2a = zeros(n)
scores2b = zeros(n)
for (x,y,z,wid) in trips:
    i = wids.index(wid)
    counts[i]+=0.02
    if x==y:
        scores2a[i]+=1
    if x==z:
        scores2b[i]+=1
scores2c = scores2b/(scores2a+scores2b)


bad_workers = []
good_workers = []
for i in range(n):
    if t[i]>0.988 and scores2c[i]<0.03:
        good_workers.append(i)
    else:
         bad_workers.append(i)

print len(bad_workers),len(good_workers)



really_bad_workers= bad_workers[:]

for i in bad_workers:
    if scores2c[i]<0.05:
        really_bad_workers.remove(i)


#plt.errorbar(range(1,51),times,yerr=times2)
#plt.plot(t,counts,'ro')


def reject_work(wids,label=None):
    label = label or turk.get_last_label()
    file = open(turk.log_root+"/"+label+".results","r")
    blah = csv.DictReader(file,delimiter='\t')
    aids = []
    for r in blah:
        wid = r['workerid']
        if wid in wids:
            aids.append(r['assignmentid'])       
    file.close()
    ttext = ""
    for aid in aids:
        st = "rejectWork -assignment "+aid+' -force'
        text = tools.my_run(st,turk.turk_root).strip()    
        my_log("[REJECT WORK]"+st+text+"\n")
        ttext+=st+"\n"+text+"\n"
    return ttext


M3 = trips2M3(trips)
M4 = (M3+1)/2
ins = [(i,j) for i in range(26) for j in range(i)]
M5 = array([[M4[k][i][j] for (i,j) in ins] for k in range(26)])


#h = []
#for a in range(26):
#    for b in range(26):
#        for c in range(26):
#            h.append(int(M3[a][b][c]*60))
#plt.hist(h)
#plt.show()

print len(trips)
r = 0
s = 0
for (a,b,c,wid) in trips:
    if wid in [wids[i] for i in good_workers]:
        r+=1
    else:
        s+=1
print r,s

plt.plot(counts[good_workers],t[good_workers],'wo')
plt.plot(counts[bad_workers],t[bad_workers],'bo')
plt.show()


class Generic:
   pass


class PCA( Tkinter.Frame ):
    def __init__( self, data, (com1,com2)=(0,1) ):
        Tkinter.Frame.__init__( self )
        self.pack( expand = Tkinter.YES, fill = Tkinter.BOTH )
        self.master.title( "FaceX" )
        self.master.geometry( "+0+0" )

        self.base=""

        self.f2 = Tkinter.Frame(self)
        self.f2.pack(side= Tkinter.LEFT  , fill=Tkinter.Y)
        

#        self.thumbs_up = PhotoImage(file="c:/temp/thumbsup.gif")
#        self.thumbs_down = PhotoImage(file="c:/temp/thumbsdown.gif")
        
        self.back = "#%02x%02x%02x" % (110, 110, 110)


        # create Canvas component
        w=1200
        h=850
        self.canvas = Tkinter.Canvas(self, width =w, height =h,relief =Tkinter.RIDGE, \
                             background = self.back, borderwidth =1)

      
        self.canvas.pack(side=Tkinter.RIGHT)
    
    #    self.canvas.bind( "<B1-Motion>", self.move )

        # bind mouse dragging event to Canvas
#        self.canvas.bind( "<ButtonPress-1>", self.down )
#        self.canvas.bind( "<ButtonRelease-1>", self.up )
#        self.canvas.focus_set()


#       self.canvas.create_oval( x1, y1, x2, y2, tag = "node", fill="white" )

#        u = lle_projected_data[:,0].tolist()
#        v = lle_projected_data[:,1].tolist()
        u = data.Vh[com1]
        v = data.Vh[com2]
        
        minu = min(u)
        maxu = max(u)
        minv = min(v)
        maxv = max(v)
        cx = (minu+maxu)/2
        cy = (minv+maxv)/2
        wx = (maxu-minu)*0.6 
        wy = (maxv-minv)*0.6

        self.ims = []
        
        for i in range(data.n):
           # print ids[i]
            im = Image.open(data.img_src[i])
            im = im.resize(((im.size[0]*100)/im.size[1],100))
            
            ## now make the white invisible (if you want!)
            im = im.convert('RGBA')
            source = im.split()                 # split the image into layers
            mask = im.point(lambda i: i < 255)  # kluge
            source[3].paste(mask)               # put mask into the alpha channel
            im = Image.merge(im.mode, source)   # build a new multiband image
            ##
            
            self.ims.append(ImageTk.PhotoImage(im))
            self.canvas.create_image(int(w/2 + ((u[i]-cx)*w)/wx/2),int(h/2+((v[i]-cy)*h)/wy/2),image=self.ims[-1],tags=("id:"+str(i)))
        
        
def go_PCA(com1=0,com2=1):
    data = Generic()
    data.n = 26
    data.img_src = [ "C:/vision/calibrialpha/calibri-"+chr(97+i)+".png"  for i in range(data.n) ]
    data.M = zeros((26,26))
    for (a,b,c,wid) in trips:
        data.M[a,b]+=1
        data.M[a,c]-=1
        data.M[b,a]+=1
        data.M[c,a]-=1        
    tools.center_mat(data.M)
    [data.U,data.sss,data.Vh]=linalg.svd(data.M.T)
    PCA(data,(com1,com2)).mainloop()

#go_PCA()


###print reject_work(find_overworkers(trips1))
