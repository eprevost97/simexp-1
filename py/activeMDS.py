import numpy as np 
import scipy as sp 
import scipy.linalg
import matplotlib as mpl
import matplotlib.pyplot as plt
import random, tools, glob
import os

random.seed(10)

mode = 0 

if mode==0:
    print "Mode: 1/(1+exp(Sac-Sab))"
if mode==1:
    print "Mode: 1/(1+exp(Sbb^2-Scc^2+2Sac-2Sab))"
if mode==2:
    print "Mode: (1+Saa+Scc-2Sac)/(2+2Saa+Sbb+Scc-2Sab-2Sac)"

 


def create_rand_tree(depth):
    if depth==0:
        return []
    zeros = [0]*(2*(2**(depth-1)-1))
    rt = create_rand_tree(depth-1)
    if random.randrange(2):
        return [0,1] + zeros+rt
    return [1,0] + rt+zeros
        

#data is row vectors, unit length, 
#squared distance is like a depth-d binary tree!
def create_fake_tree_data(n,depth):
    data = np.zeros([n,2*(2**depth-1)])
    for i in range(n):
        data[i] = create_rand_tree(depth)
    return data*(1./np.sqrt(depth))
    
        
# true means a is more similar to b than c
def fake_sim_exp(data,a,b,c):
    Sab = np.dot(data[a],data[b])
    Sac = np.dot(data[a],data[c])
    return random.random()< 1./(1.+np.exp(Sac-Sab))

def fake_sim_exp2(data,a,b,c):
    d = data[a]-data[c]
    dac = 1.+np.dot(d,d)
    d = data[a]-data[b]
    dab = 1.+np.dot(d,d)
    return random.random()< 1./(1.+np.exp(dab-dac))


def fake_sim(data,a,b,c):
    if mode==0:
        Sab = np.dot(data[a],data[b])
        Sac = np.dot(data[a],data[c])
        return random.random()< 1./(1.+np.exp(Sac-Sab))
    if mode==1:
        d = data[a]-data[c]
        dac = 1.+np.dot(d,d)
        d = data[a]-data[b]
        dab = 1.+np.dot(d,d)
        return random.random()< 1./(1.+np.exp(dab-dac))


def fake_sim_rel(data,a,b,c):
    d = data[a]-data[c]
    dac = 1.+np.dot(d,d)
    d = data[a]-data[b]
    dab = 1.+np.dot(d,d)
    return random.random()< dac/(dac+dab)

def p(S,a,b,c):
    if mode==0:
        return 1./(1.+np.exp(S[a,c]-S[a,b]))
    if mode==1:
        return 1./(1.+np.exp(S[b,b]-S[c,c]+2*S[a,c]-2*S[a,b]))

#add eta times the gradient of an a~b/c trip to matrix g
def exp_grad(S,g,a,b,c):
    t = 1/(1.+np.exp(S[a,b]-S[a,c]))
    g[a,b]+=t
    g[a,c]-=t
    g[b,a]+=t
    g[c,a]-=t

def exp2_grad(S,g,a,b,c):
    t = 1./(1.+np.exp(S[c,c]-S[b,b]+2*S[a,b]-2*S[a,c]))
    g[b,b]-=t
    g[c,c]+=t
    g[a,b]+=t
    g[a,c]-=t
    g[b,a]+=t
    g[c,a]-=t



def log_score_exp(trips,S):
    ls = 0.
    for (a,b,c) in trips:
        ls+=np.log2(1.+np.exp(S[a,c]-S[a,b]))
    return ls/len(trips)

def log_score_exp2(trips,S):
    ls = 0.
    for (a,b,c) in trips:
        ls+=np.log2(1.+np.exp(S[b,b]-S[c,c]+2*S[a,c]-2*S[a,b]))
    return ls/len(trips)


def log_score_rel(trips,S):
    ls = 0.
    for (a,b,c) in trips:
        d = data[a]-data[c]
        dac = 1.+np.dot(d,d)
        d = data[a]-data[b]
        dab = 1.+np.dot(d,d)
        ls+=np.log2(dac/(dac+dab))
    return ls/len(trips)

def class_score_exp(trips,S):
    ls = 0.
    for (a,b,c) in trips:
        if S[a,b]>S[a,c]:
            ls+=1.
        if S[a,b]==S[a,c]:
            ls+=0.5
    return ls/len(trips)
    
def class_score_exp2(trips,S):
    ls = 0.
    for (a,b,c) in trips:
        if S[c,c]+2*S[a,b]>S[b,b]+2*S[a,c]:
            ls+=1.
        if S[c,c]+2*S[a,b]==S[b,b]+2*S[a,c]:
            ls+=0.5
    return ls/len(trips)
    
    
# tracenorm is an average
def grad_proj(trips,test_trips,its,step_size = 100.,tracenorm=15.,Sinit = None):
    if mode==0:
        grad = exp_grad
        score = log_score_exp
    if mode==1:
        grad = exp2_grad
        score = log_score_exp2
    n = np.max(trips)+1
    if Sinit==None:
        S = np.zeros([n,n])
    else:
        S = Sinit+0.
    score1 = score(trips,S)
    for i in range(its):
        print "Iteration",i,"step size",step_size, "tracenorm",tracenorm,"scores:",score(trips,S),score(test_trips,S)
        #print S
        if i%6==3:
            score2 = score(trips,S)
            step_size *=0.6
        if i%6==0 and i!=0:
            score3 = score(trips,S)
            if score1-score2>score2-score3:
                step_size*=2
            score1 = score3
        g = np.zeros([n,n])
        for (a,b,c) in trips:
            grad(S,g,a,b,c)
        print scipy.linalg.norm(g)
        S += step_size*g
        S = (S+S.T)/2
        #print "expensive step..."
        [v,M] = np.linalg.eigh(S)
        m = len(v)
        #print "              ... done"
        #first project down to svd and tracenorm
        for j in range(m):
            if(v[j]<0.): 
#                print "******* ZEROING"
                v[j]=0.
            else:
                s = sum(v)
                if s>tracenorm*n:
#                    import pdb; pdb.set_trace()
#                    print "+++++++ SHRINKING"
                    vv = min(v[j],(s-tracenorm*n)/(m-j))
                    for k in range(j,m):
                        v[k]-=vv
                else:
                    break
        S = np.dot(np.dot(M,np.diag(v)),M.T)
    return S

memoize = None
def project_to_t(S,t,eps=0.001):
    global memoize
    n = S.shape[0]
    if memoize==None or memoize.shape[0]!=n:
        memoize=np.zeros(n)
    err = eps+1
    j = 0
    while err>eps:
        j+=1
        [v,M] = np.linalg.eigh(S+np.diag(memoize))
        for i in range(n):
            if v[i]>=0:
                break
            v[i]=0
        T = np.dot(np.dot(M,np.diag(v)),M.T)
        memoize += (t-np.diag(T))
        err = max(np.abs(t-np.diag(T)))
    print j,"Max diag difference from",t,"is",err
    return T
    




def grad_proj2(trips,test_trips,its,step_size = 100.,tracenorm=15.,Sinit = None):
    if mode==0:
        grad = exp_grad
        score = log_score_exp
    if mode==1:
        grad = exp2_grad
        score = log_score_exp2
    n = np.max(trips)+1
    if Sinit==None:
        S = np.eye(n)*tracenorm
    else:
        S = Sinit+0.
    score1 = score(trips,S)
    for i in range(its):
        print "Iteration",i,"step size",step_size, "tracenorm",tracenorm,"scores:",score(trips,S),score(test_trips,S)
        #print S
        if i%6==3:
            score2 = score(trips,S)
            step_size *=0.6
        if i%6==0 and i!=0:
            score3 = score(trips,S)
            if score1-score2>score2-score3:
                step_size*=2
            score1 = score3
        g = np.zeros([n,n])
        for (a,b,c) in trips:
            grad(S,g,a,b,c)
        print "gradient norm",scipy.linalg.norm(g)
        S += step_size*g
        S = (S+S.T)/2
        #print "expensive step..."
        [v,M] = np.linalg.eigh(S)
        m = len(v)
        #print "              ... done"
        #first project down to svd and tracenorm
        S=project_to_t(S,tracenorm)
    return S
    

def create_rand_trips(data,ntrips):
    trips = []
    n = data.shape[0]
    for i in range(ntrips):
        a = b = c = 0
        while a==b or a==c or b==c:
            a = random.randrange(n)
            b = random.randrange(n)
            c = random.randrange(n)        
        trips.append((a,b,c) if fake_sim_exp(data,a,b,c) else (a,c,b))
    return trips

def create_rand_trips2(data,ntrips):
    trips = []
    n = data.shape[0]
    for i in range(ntrips):
        a = b = c = 0
        while a==b or a==c or b==c:
            a = random.randrange(n)
            b = random.randrange(n)
            c = random.randrange(n)        
        trips.append((a,b,c) if fake_sim_exp2(data,a,b,c) else (a,c,b))
    return trips



#
#data = create_fake_tree_data(5,3)*3
#print data
#trips = create_rand_trips2(data,10000)
#test_trips = create_rand_trips2(data,1000)
#print "data score on trips",log_score_exp2(trips,np.dot(data,data.T)),class_score_exp2(trips,np.dot(data,data.T))
#
#S = grad_proj(trips,test_trips,exp2_grad,log_score_exp2,150,step_size=0.01,tracenorm=15)#,Sinit=np.dot(data,data.T))
#print S-np.dot(data,data.T)


def read_out_files(fnames):
    if type(fnames)!=list:
        fnames = [fnames]
    res = []
    for f in fnames:
        res += [map(int,i.split()[:3]) for i in tools.my_read(f).strip().splitlines()]
    return res

postfilename = "c:/temp/lps_exp.npy"
def posts(S,trips,readem=True):
    if readem and os.path.exists(postfilename):
        return np.load(postfilename)        
    n = S.shape[0]
    lps = np.zeros([n,n])
    counts = np.zeros(n)
    k=0
    for (a,b,c) in trips:
        k+=1
        if k%100==0:
            print k,"/",len(trips)
        counts[a]+=1
        counts[b]+=1
        counts[c]+=1
        for i in range(n):
            lps[a,i]-=np.log2(p(S,i,b,c))
            lps[b,i]-=np.log2(p(S,a,i,c))
            lps[c,i]-=np.log2(p(S,a,b,i))
#    for i in range(n):
#        for j in range(n):
#            lps[i,j]/=counts[i]
    np.save(postfilename,lps) 
    print "Saved in",postfilename 
    return lps


def show_posts(S,trips,readem=True):
    n = S.shape[0]
    st = "<html><head></head><body><table border=1>"
    lps = posts(S,trips,readem)
    for i in range(n):
        st+="<tr>"
        r = [(lps[i,j],j) for j in range(n)]
        r.sort()
        r = [(-10000,i)]+r
        ttt = np.array([2**(lps[i,i]-lps[i,j]) for j in range(n)])
        ttt /= sum(ttt)
        for j in range(n):
            k=r[j][1]
            st+='<td><img alt="p '+str(ttt[k])+'" src="'+im_filename(k)+'"></td>'
        st+="</tr>\n"
    st+= "</table></body></html>"
    tools.my_write("c:/temp/posts.html",st)





def doppel_trips(S,trips,radius):
    lps = posts(S,trips,readem=True) #posterior distribution
    n = S.shape[0]
    st = "<html><head></head><body><table>"  
    for a in range(100):
        prior = np.array([2**(lps[a,a]-lps[a,j]) for j in range(n)])
        prior[a]=0
        prior /= sum(prior)
        # p is posteriors
        for rrr in range(300):
            b = random.randrange(n)
            c = random.randrange(n)
            if b==c or b==a or c==a:
                continue
            #evaluate quality of trip a b c for a's uncertainty           
            pb = 0.
            for j in range(n):
                pb += prior[j]*p(S,j,b,c)
            pc = 1-pb    
            u = 0
            for j in range(n):
                t = p(S,j,b,c)
                if t>1:
                    print "UH OH: ",j,b,c,S[j,j]+S[b,b]-2.*S[j,b],S[j,j]+S[b,b]-2.*S[j,b]
                if prior[j]>1e-17:
                    u += prior[j]*t*np.log2(pb/(prior[j]*t)) + prior[j]*(1-t)*np.log2(pc/(prior[j]*(1-t)))
            if rrr==0 or u<best:
                best = u
                bestb = b
                bestc = c
                bestpb = pb
        print "Best entropy",best
        st+="<tr>"
        st+='<td><img src="'+im_filename(a)+'"></td>'
        st+='<td><img src="'+im_filename(bestb)+'"></td>'
        st+='<td><img src="'+im_filename(bestc)+'"></td>'
        st+='<td><table border=1>'
        b = bestb
        c = bestc
        t = [ (prior[j]*(p(S,j,b,c)-bestpb),j) for j in range(n)]
        t.sort()
        st+='<tr>'
        for j in range(20):
            st+='<td><img src="'+im_filename(t[j][1])+'" alt="'+str(t[j][0])+'"></td>'
        st+='</tr>'
        st+='<tr>'
        for j in range(20):            
            st+='<td><img src="'+im_filename(t[-j-1][1])+'" alt="'+str(t[-j-1][0])+'"></td>'
        st+='</tr>'
        st+="</table></td></tr>\n"
        tools.my_write("c:/temp/doppels_exp"+str(radius)+".html",st+ "</table></body></html>")
        print "c:/temp/doppels_exp"+str(radius)+".html"



def test_small_ties():
    radius = 1.
    print "Testing neckties"
    adaptive_trips = read_out_files(glob.glob("c:/sim/turkexps/neckties/small/*.out"))
    print len(adaptive_trips),"adaptive trips"
    random_trips = read_out_files(glob.glob("c:/sim/turkexps/neckties/small/random/*.out"))
    print len(random_trips),"random trips"
    control_trips = read_out_files(glob.glob("c:/sim/turkexps/neckties/small/control/*.out"))
    print len(control_trips),"control trips"
    S=grad_proj2(random_trips,control_trips,10,step_size=1,tracenorm=radius)
    show_nn(S)
    show_posts(S,random_trips)
    doppel_trips(S,random_trips,radius)
    
filenames = None
fdir = "c:\\data\\neckties"
def im_filename(j):
    global filenames
    if filenames==None:
        filenames = tools.my_read(fdir+"/ids.txt").strip().splitlines()
    return fdir+"\\"+filenames[j]



def show_nn(S):
    n = S.shape[0]
    st = "<html><head></head><body><table border=1>"
    for i in range(n):
        st+="<tr>"
        dists = []
        for j in range(n):
            dists.append((S[i,i]+S[j,j]-2*S[i,j],j))
        dists.sort()
        for j in range(n/5):
            st+='<td><img src="'+im_filename(dists[j][1])+'"></td>'
        st+="</tr>\n"
    st+= "</table></body></html>"
    tools.my_write("c:/temp/nn.html",st)
        


test_small_ties()