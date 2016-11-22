import numpy as np
import matplotlib as mpl
import scipy.interpolate as sin
import scipy.optimize as opt
import scipy.ndimage as snd
import cv2

def bilateralFilter(F, d=10, si=1.0, sd=1.0):
    '''
    A wraper for the openCV bilateral filter.  Applies a non-linear,
    edge-preserving filter to a 2D image.  If input is a 3D dataset, this will
    apply the filter to each layer by iterating over the first index.

    Inputs:
        d - Diameter of pixel neighborhood used in filtering.
        si - Width of gaussian in pixel intensity space.
        sd - Width of gaussian in real space.

    Usage: output = bilateralFilter(image, d=10, si=1.0, sd=1.0)

    Issues: If data dominated by one number (e.g. center pixel in the FT)
    then filter does not work. 
    '''
    def filter2d(img, d, si, sd):
        norm = float(np.max(img))
        data = np.float32(img/norm)
        out = cv2.bilateralFilter(data, d, si, sd)
        return norm * np.float64(out)
    if len(F.shape) is 2:
        return filter2d(F, d, si, sd)
    if len(F.shape) is 3:
        out = np.zeros_like(F)
        for ix, layer in enumerate(F):
            out[ix] = filter2d(layer, d, si, sd)
        return out
    else:
        print('ERR: Input must be 2D or 3D numpy array.')

def saturate(level_low=0, level_high=None):
    '''
    Adjusts color axis of in current handle.  Calculates a probablility density function for the data in current axes handle.  Uses upper and lower thresholds to find sensible c-axis limits.  Thresholds are between 0 and 100.  If unspecified the upper threshold is assumed to be 100 - lower threshold.
    
    Usage:  pcolormesh(image)
            saturate(10)
    '''
    level_low = float(level_low) / 200.0
    if level_high is None:
        level_high = 1-level_low
    else:
        level_high = (float(level_high)+100) / 200.0
    imageObjects = mpl.pyplot.gca().get_children()
    data = []
    images = []
    for item in imageObjects:
        if isinstance(item, (mpl.image.AxesImage, mpl.collections.QuadMesh)):
            images.append(item)
            data.append(item.get_array().ravel())
    y = sorted(np.array(data).ravel())
    y_density = np.absolute(y) / sum(np.absolute(y))
    pdf = np.cumsum(y_density)
    y_low = np.absolute(level_low - pdf)
    y_high = np.absolute(level_high - pdf)
    c_low = y[np.argmin(y_low)]
    c_high = y[np.argmin(y_high)]
    for image in images:
        image.set_clim(c_low, c_high)


def azimuthalAverage(F,x0,y0,r,theta = np.linspace(0,2*np.pi,500)):
    ''' Uses 2d interpolation to average F over an arc defined by theta for every r value starting from x0,y0. '''
    f = sin.interp2d(np.arange(F.shape[1]), np.arange(F.shape[0]), F, kind='linear')
    Z = np.zeros_like(r); fTheta = np.zeros_like(theta)
    for ix, r0 in enumerate(r):
        x = r0*np.cos(theta) + x0
        y = r0*np.sin(theta) + y0
        for iy, (xn,yn) in enumerate(zip(x,y)):
            fTheta[iy] = f(xn,yn)
        Z[ix] = np.mean(fTheta)
    return Z



def azimuthalAverageRaw(F,x0,y0,rmax):
    ''' Azimuthally average beginning at x0,y0 to a maximum distance rmax'''
    f=[]; p=[]; R=[]; FAvg=[]
    for x in range(F.shape[1]):
        for y in range(F.shape[0]):
            r = np.sqrt((x-x0)**2 + (y-y0)**2)
            if r <= rmax:
                p.append(r)
                f.append(F[y,x])
    for r0 in set(np.sort(p)):
        R.append(r0)
        allFVals = [f0 for ix,f0 in enumerate(f) if p[ix] == r0]
        FAvg.append(np.mean(allFVals))  
    R = np.array(R); ixSorted = R.argsort()  
    return R[ixSorted], np.array(FAvg)[ixSorted]


def binData(x,y,nBins):
    ''' For any randomly sampled data x,y, return a histogram with linear bin spacing'''
    # Issues: What if there are no elements in a bin? 
    binSize = max(x)/nBins; X=[];Y=[]
    for n in range(nBins):
        allBinYVal = []
        minR = n * binSize; maxR = (n+1) * binSize; 
        for ix,R in enumerate(x):
            if R >= minR and R < maxR:
                allBinYVal.append(y[ix])
        X.append( (minR + maxR) / 2.0 )
        Y.append( np.mean(allBinYVal) )
    return X,Y  


def linecut(F, x1, y1, x2, y2, n):
    ''' Use linear interpolation on a 2D data set F, sample along a line from (x1,y1) to (x2,y2) in n points

Usage:  x_linecut, y_linecut = linecut(image, x1, y1, x2, y2, n)
    '''
    x = np.arange(F.shape[0])
    y =  np.arange(F.shape[1])
    cen = np.sqrt((x1-x2)**2 + (y1-y2)**2) / 2.0
    r = np.linspace(-1*cen, cen, n)
    f = sin.interp2d(x, y, F, kind = 'linear')
    xval = np.linspace(x1, x2, n)
    yval = np.linspace(y1, y2, n)
    z = [f(xval[ix],yval[ix])[0] for ix in range(n)]
    return r, np.array(z)


def squareCrop(image,m=None):
    ''' Crops a 2D image to be mxm, where m is an even integer. '''
    image = np.array(image)
    a,b =image.shape
    if m is None: m = min(a,b)
    if m%2 != 0: m-=1
    imageCrop = image[:m,:m]
    return imageCrop


def lineCrop(x, y, cropRange):
    ''' Crops a 1D line using a list of start, stop values. Can delete sections of data
        Usage: xCrop,yCrop = lineCrop(x, y, [start,stop,start,stop,...])'''
    cropIndex = []; xCrop = []; yCrop = []
    for cropVal in cropRange:
        a = [ix for ix,x0 in enumerate(x) if x0 >= cropVal]
        if a == []:
            if cropVal <= x[0]: a = [0]
            else: a = [len(x)-1]
        cropIndex.append(a[0])
    for ix in range(0,len(cropIndex),2):
        xCrop += x.tolist()[cropIndex[ix]:cropIndex[ix+1]+1]
        yCrop += y.tolist()[cropIndex[ix]:cropIndex[ix+1]+1]
    return np.array(xCrop), np.array(yCrop)


def removePolynomial1d(y, n, x=None, fitRange=None):
    ''' Removes a background polynomial of degree n to the line y(x) in the range fitRange (optional).
        Usage: yCorrected = removePolynomial1d(y, n)'''
    if x is None: x=np.linspace(0, 1, len(y))
    if fitRange is None: fitRange = [x[0],x[-1]]
    xBkg,yBkg = lineCrop(x,y,fitRange)
    polyCoeff = np.polyfit(xBkg,yBkg,n)
    polyBackgroundFunction = np.poly1d(polyCoeff)
    return y - polyBackgroundFunction(x)

def lineSubtract(data, n):
    '''
    Remove a polynomial background from the data line-by-line.  If the data is
    3D (eg. 3ds) this does a 2D background subtract on each layer
    independently.  Input is a numpy array. 
    
    Usage: A.z = lineSubtract(A.Z, 2)
    '''
    def subtract_2D(data, n):
        output = np.zeros_like(data)
        for ix, line in enumerate(data):
            output[ix] = removePolynomial1d(line, n)
        return output
    if len(data.shape) is 3:
        output = np.zeros_like(data)
        for ix, layer in enumerate(data):
            output[ix] = subtract_2D(layer, n)
        return output
    elif len(data.shape) is 2:
        return subtract_2D(data, n)


def fitGaussian2d(data, p0):
    ''' Fit a 2D gaussian to the data with initial parameters p0. '''
    data = np.array(data)
    def gauss(xy,amplitude,x0,y0,sigmaX,sigmaY,theta,offset):
        x,y = xy
        x0=float(x0);y0=float(y0)
        a =  0.5*(np.cos(theta)/sigmaX)**2 + 0.5*(np.sin(theta)/sigmaY)**2 
        b = -np.sin(2*theta)/(2*sigmaX)**2 + np.sin(2*theta)/(2*sigmaY)**2
        c =  0.5*(np.sin(theta)/sigmaX)**2 + 0.5*(np.cos(theta)/sigmaY)**2
        g = offset+amplitude*np.exp(-( a*(x-x0)**2 -2*b*(x-x0)*(y-y0) + c*(y-y0)**2 ))
        return g.ravel()
    x = range(data.shape[0]);  y = range(data.shape[1])
    X,Y = np.meshgrid(x,y)
    popt, pcov = opt.curve_fit(gauss, (X,Y), data.ravel(), p0=p0)
    return gauss((X,Y),*popt).reshape(data.shape)


def findOtherBraggPeaks(FT, bpx, bpy, n = 1):
    '''Once one bragg peak is found this retruns n other bragg peak harmonics by symmetry of the Fourier transform.'''
    N  = range(-n,0)+range(1,n+1)
    Bpx = [];  Bpy = []
    cenX = FT.shape[1]/2.0;  cenY = FT.shape[0]/2.0 
    rScale = np.sqrt((bpx-cenX)**2 + (bpy-cenY)**2)
    dx = bpx - cenX;  dy = bpy - cenY
    for i in N:
        Bpx.append(cenX + i*dx)
        Bpy.append(cenY + i*dy)
    return Bpx,Bpy,rScale


def findPeaks(x,y,n=1,nx=1e3):
    ''' Finds n peaks in a given 1D-line by finding where the derivative crosses zero. '''
    f = sin.interp1d(x,y,kind='linear')
    xx = np.linspace(x[0],x[-1],nx); fx = f(xx)
    df = np.gradient(fx)
    x0=[]; y0=[]
    for ix, df0 in enumerate(df):
        if ix != 0:
            if df0/df[ix-1] < 0: 
                x0.append(xx[ix])
                y0.append(fx[ix])
    xn = [x for (y,x) in sorted(zip(y0,x0))][::-1][:n]
    yn = sorted(y0)[::-1][:n]			
    if xn == []: xn = [0] * n
    if yn == []: yn = [0] * n
    return xn, yn


def removeGaussian2d(image, x0, y0, sigma):
    '''Removes a isotropic gaussian of width sigma centered at x0,y0 from image.'''
    x0 = float(x0); y0 = float(y0)
    a = - 0.5 / sigma**2
    x = np.arange(image.shape[0]); y = np.arange(image.shape[1])
    X,Y = np.meshgrid(x,y)
    g = np.exp( a*(X-x0)**2 + a*(Y-y0)**2 )
    return image * (1 - g)


def fitGaussians1d(x, y, p0):
    ''' Fits n gaussians to the line y(x), with guess parameters p0 = [amp_1,mu_1,sigma_1,amp_2,mu_2,sigma_2,...]'''
    def gaussn(x, *p):
        g = np.zeros_like(x)
        for i in range(0,len(p),3):
            amp = abs(float( p[i] ))
            mu = float( p[i+1] )
            sigma = float( p[i+2] )
            g += amp * np.exp(- (x-mu)**2 / (2.0*sigma**2) ) 
        return g
    p,cov = opt.curve_fit(gaussn, x, y, p0)
    return p,gaussn(x,*p)


def foldLayerImage(layerImage,bpThetaInRadians=0,n=4):
    ''' Returns a n-Fold symmetric layer image, where the fold directions are defined by bpTheta. '''
    B = np.zeros_like(layerImage)
    bpTheta = bpThetaInRadians * (180.0/np.pi) + 45
    for ix,layer in enumerate(layerImage):
        if bpTheta != 0: layer = snd.interpolation.rotate(layer,bpTheta,reshape = False)
        step1 = (layer + layer.T) / 2.0
        step2 = (step1 + np.flipud((np.fliplr(step1)))) / 2.0
        step3 = (step2 + np.fliplr(step2)) / 2.0
        options = { 1 : step1,
                2 : step2,
                4 : step3  }
        B[ix] = options.get(n,0)
        if bpTheta != 0: B[ix] = snd.interpolation.rotate(B[ix],-bpTheta,reshape = False)
    if n not in options.keys(): print('{:}-fold symmetrization not yet implemented'.format(n))
    return B

def quickFT(data, n=None, zero_center=True):
    '''
    A hassle-free FFT for 2D or 3D data.  Useful for quickly computing the QPI
    patterns from a DOS map. Returns the absolute value of the FFT for each
    layer in the image. Has the option of setting the center pixel to zero and
    the option to n-fold symmetrize the output.

    Usage: A.qpi = quickFT(A.LIY, zero_center=True, n=None)
    '''
    def ft2(data):
        ft = np.fft.fft2(data)
        if zero_center:
            ft[0,0] = 0
        return np.absolute(np.fft.fftshift(ft))
    if len(data.shape) is 2:
        if n is None:
            return ft2(data)
        else:
            return symmetrize(ft2(data), n)
    if len(data.shape) is 3:
        output = np.zeros_like(data)
        for ix, layer in enumerate(data):
            output[ix] = ft2(layer)
        if n is None:
            return output
        else:
            return symmetrize(output, n)
    else:
        print('ERR: Input must be 2D or 3D numpy array.')


def symmetrize(F, n):
    '''
    Applies n-fold symmetrization to the image by rotating clockwise and
    anticlockwise by an angle 2pi/n, then applying a mirror line.  Works on 2D
    and 3D data sets, in the case of 3D each layer is symmetrzed 
    '''
    def sym2d(F, n):

        angle = 360.0/n
        out = np.zeros_like(F)
        for ix in range(n):
            out += snd.rotate(F, angle*ix, reshape=False)
            out += snd.rotate(F, -angle*ix, reshape=False)
        out /= 4*n
        return out
    if len(F.shape) is 2:
        return sym2d(F, n)
    if len(F.shape) is 3:
        out = np.zeros_like(F)
        for ix, layer in enumerate(F):
            out[ix] = sym2d(layer, n)
        return out
    else:
        print('ERR: Input must be 2D or 3D numpy array.')

