def alpha_mart(x: np.array, N: int, mu: float=1/2, eta: float=1-np.finfo(float).eps, u: float=1, \
               estim: callable=shrink_trunc) -> np.array :
    '''
    Finds the ALPHA martingale for the hypothesis that the population 
    mean is less than or equal to t using a martingale method,
    for a population of size N, based on a series of draws x.
    
    The draws must be in random order, or the sequence is not a martingale under the null
    
    If N is finite, assumes the sample is drawn without replacement
    If N is infinite, assumes the sample is with replacement

    Parameters
    ----------
    x : list corresponding to the data
    N : int
        population size for sampling without replacement, or np.infinity for sampling with replacement
    mu : float in (0,1)
        hypothesized fraction of ones in the population
    eta : float in (t,1) 
        alternative hypothesized population mean
    estim : callable
        estim(x, N, mu, eta, u) -> np.array of length len(x), the sequence of values of eta_j for ALPHA
               
    Returns
    -------   
    terms : array
        sequence of terms that would be a nonnegative supermartingale under the null
    '''
    S = np.insert(np.cumsum(x),0,0)[0:-1]  # 0, x_1, x_1+x_2, ...,  
    j = np.arange(1,len(x)+1)              # 1, 2, 3, ..., len(x)
    m = (N*mu-S)/(N-j+1) if np.isfinite(N) else mu   # mean of population after (j-1)st draw, if null is true 
    etaj = estim(x, N, mu, eta, u) 
    with np.errstate(divide='ignore',invalid='ignore'):
        terms = np.cumprod((x*etaj/m + (1-x)*(u-etaj)/(u-m))/u)
    terms[m<0] = np.inf
    return terms

def sprt_mart(x : np.array, N : int, mu : float=1/2, eta: float=1-np.finfo(float).eps, \
              u: float=1, random_order = True):
    '''
    Finds the p value for the hypothesis that the population 
    mean is less than or equal to mu against the alternative that it is eta,
    for a population of size N of values in the interval [0, u].
    
    Generalizes Wald's SPRT for the Bernoulli to sampling without replacement and to bounded
    values rather than binary values.

    If N is finite, assumes the sample is drawn without replacement
    If N is infinite, assumes the sample is with replacement
    
    Data are assumed to be in random order. If not, the calculation for sampling without replacement is incorrect.

    Parameters:
    -----------
    x : binary list, one element per draw. A list element is 1 if the 
        the corresponding trial was a success
    N : int
        population size for sampling without replacement, or np.infinity for 
        sampling with replacement
    theta : float in (0,u)
        hypothesized population mean
    eta : float in (0,u)
        alternative hypothesized population mean
    random_order : Boolean
        if the data are in random order, setting this to True can improve the power.
        If the data are not in random order, set to False
    '''
    if any((xx < 0 or xx > u) for xx in x):
        raise ValueError(f'Data out of range [0,{u}]')
    if np.isfinite(N):
        if not random_order:
            raise ValueError("data must be in random order for samples without replacement")
        S = np.insert(np.cumsum(x),0,0)[0:-1]  # 0, x_1, x_1+x_2, ...,  
        j = np.arange(1,len(x)+1)              # 1, 2, 3, ..., len(x)
        m = (N*mu-S)/(N-j+1)                   # mean of population after (j-1)st draw, if null is true
    else:
        m = mu
    with np.errstate(divide='ignore',invalid='ignore'): 
        terms = np.cumprod((x*eta/m + (u-x)*(u-eta)/(u-m))/u) # generalization of Bernoulli SPRT
    terms[m<0] = np.inf                        # the null is surely false
    return terms

def shrink_trunc(x: np.array, N: int, mu: float=1/2, nu: float=1-np.finfo(float).eps, u: float=1, c: float=1/2, 
                 d: float=100) -> np.array: 
    '''
    apply the shrinkage and truncation estimator to an array
    
    sample mean is shrunk towards nu, with relative weight d times the weight of a single observation.
    estimate is truncated above at u-u*eps and below at mu_j+e_j(c,j)
    
    S_1 = 0
    S_j = \sum_{i=1}^{j-1} x_i, j > 1
    m_j = (N*mu-S_j)/(N-j+1) if np.isfinite(N) else mu
    e_j = c/sqrt(d+j-1)
    eta_j =  ( (d*nu + S_j)/(d+j-1) \vee (m_j+e_j) ) \wedge u*(1-eps)
    
    Parameters
    ----------
    x : np.array
        input data       
    mu : float in (0, 1)
        hypothesized population mean
    eta : float in (t, 1)
        initial alternative hypothethesized value for the population mean
    c : positive float
        scale factor for allowing the estimated mean to approach t from above
    d : positive float
        relative weight of nu compared to an observation, in updating the alternative for each term
    '''
    S = np.insert(np.cumsum(x),0,0)[0:-1]  # 0, x_1, x_1+x_2, ...,  
    j = np.arange(1,len(x)+1)              # 1, 2, 3, ..., len(x)
    m = (N*mu-S)/(N-j+1) if np.isfinite(N) else mu   # mean of population after (j-1)st draw, if null is true 
    return np.minimum(u*(1-np.finfo(float).eps), np.maximum((d*nu+S)/(d+j-1),m+c/np.sqrt(d+j-1)))

def test_shrink_trunc():
    epsj = lambda c, d, j: c/math.sqrt(d+j-1)
    Sj = lambda x, j: 0 if j==1 else np.sum(x[0:j-1])
    muj = lambda N, mu, x, j: (N*mu - Sj(x, j))/(N-j+1) if np.isfinite(N) else mu
    nus = [.51, .55, .6]
    mu = 1/2
    u = 1
    d = 10
    vrand =  sp.stats.bernoulli.rvs(1/2, size=20)
    v = [
        np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1]),
        np.array([1, 1, 1, 1, 1, 1, 0, 0, 0, 0]),
        vrand
    ]
    for nu in nus:
        c = (nu-mu)/2
        for x in v:
            N = len(x)
            xinf = shrink_trunc(x, np.inf, mu, nu, c=c, d=d)
            xfin = shrink_trunc(x, len(x), mu, nu, c=c, d=d)
            yinf = np.zeros(len(x))
            yfin = np.zeros(len(x))
            for j in range(1,len(x)+1):
                est = (d*nu + Sj(x,j))/(d+j-1)
                most = u*(1-np.finfo(float).eps)
                yinf[j-1] = np.minimum(np.maximum(mu+epsj(c,d,j), est), most)
                yfin[j-1] = np.minimum(np.maximum(muj(N,mu,x,j)+epsj(c,d,j), est), most)
            np.testing.assert_allclose(xinf, yinf)    
            np.testing.assert_allclose(xfin, yfin)    