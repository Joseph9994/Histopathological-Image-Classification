# -*- coding: utf-8 -*-
"""01_pre_processing_resizing512x512_IL.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1lxMaZHPGuK61OWWDpRGZIWmrHipcz_nH
"""

# INSTALLINGS

!pip install imagecodecs

!nvidia-smi

# LINKAGE TO GOOGLE DRIVE AND LIBRERIES IMPORTING

from google.colab import drive
drive.mount('/content/drive')

import os
import random
import numpy as np
import plotly.express as px
import imagecodecs

from matplotlib import pyplot as plt
from tqdm import tqdm
from skimage.io import imread, imshow, imsave
from skimage.transform import resize
from skimage.segmentation import mark_boundaries
from scipy import ndimage
from skimage.util import img_as_float,img_as_ubyte, crop
from skimage.morphology import binary_dilation
from keras.utils.np_utils import to_categorical
from skimage import measure, morphology

# DATASET UNRAR: LOADING DATASET IN COLAB

!pip install unrar
!unrar x "drive/MyDrive/cytology challenge condivisa/00_DATASET/train.rar"     # unraring training set
!unrar x "drive/MyDrive/cytology challenge condivisa/00_DATASET/validation.rar"   # unraring validation set
!unrar x "drive/MyDrive/cytology challenge condivisa/00_DATASET/test.rar"         # unraring test set

# SETTINGS OF CURRENT PRE-PROCESSING

pre_proc_name = 'IL1'  # name of current pre-processing <------------------------------- CHANGE HERE
rsz = 512  # resizing size (resize images to rsz x rsz) <-------------------------------- CHANGE HERE
NUM_CLASSES = 3 # number of classes choosen for the problem <---------------------------- CHANGE HERE

# Commented out IPython magic to ensure Python compatibility.
# STORING TRAINING SET IMAGES AND MASKS IN PROPER NDARRAY

# path
tr_IMGS_path = os.path.join('train','images')
tr_MANU_path = os.path.join('train','manual')

# extracting list of images
tr_images = sorted(os.listdir(tr_IMGS_path))

# body
X_tr = np.zeros([len(tr_images),rsz,rsz,3], dtype=np.uint8)
Y_tr = np.zeros([len(tr_images),rsz,rsz], dtype=np.uint8)
for n, id_ in tqdm(enumerate(tr_images), total=len(tr_images)):

    # loading
    img = imread(tr_IMGS_path+'/'+id_) # uint8 stained image
    manu0 = imagecodecs.imread(tr_MANU_path+'/'+id_) # N layers manual segmentations (each layer a different MM cell)

    # "compressing" segmentation annotations on a single layer
    if len(manu0.shape)==2:
      manu = np.copy(manu0[:,:])
    else:
      manu = np.copy(manu0[:,:,0])
      for j in range(1,manu0.shape[2]):
        manu[manu0[:,:,j]==255] = 255
        manu[manu0[:,:,j]==128] = 128
        manu = morphology.area_opening(manu,0.001*manu.shape[0]*manu.shape[1])  # removal of small objects erroneously annotated (single pixels or little spots)
        manu = morphology.area_closing(manu,0.001*manu.shape[0]*manu.shape[1])  # removal of small holes errouneously not annotated

    #resizing
    img = img_as_ubyte(resize(img,[rsz,rsz]))
    manu = img_as_ubyte(resize(manu,[rsz,rsz]))
    manu[manu < 80] = 0
    manu[ (manu >= 80)*(manu <= 175) ] = 1
    manu[manu > 175] = 2

    # actual storage
    X_tr[n] = np.copy(img)
    Y_tr[n] = np.copy(manu)

# Y_tr = to_categorical(Y_tr, num_classes = NUM_CLASSES, dtype='float32')  # conversion to categorical data


# STORING VALIDATION SET IMAGES AND MASKS IN PROPER NDARRAY

# path
vl_IMGS_path = os.path.join('validation','images')
vl_MANU_path = os.path.join('validation','manual')

# extracting list of images
vl_images = sorted(os.listdir(vl_IMGS_path))

# body
X_vl = np.zeros([len(vl_images),rsz,rsz,3], dtype=np.uint8)
Y_vl = np.zeros([len(vl_images),rsz,rsz], dtype=np.uint8)
for n, id_ in tqdm(enumerate(vl_images), total=len(vl_images)):

    # loading
    img = imread(vl_IMGS_path+'/'+id_)
    manu0 = imagecodecs.imread(vl_MANU_path+'/'+id_) # N layers manual segmentations (each layer a different MM cell)

    # "compressing" segmentation annotations on a single layer
    if len(manu0.shape)==2:
      manu = np.copy(manu0[:,:])
    else:
      manu = np.copy(manu0[:,:,0])
      for j in range(1,manu0.shape[2]):
        manu[manu0[:,:,j]==255] = 255
        manu[manu0[:,:,j]==128] = 128
        manu = morphology.area_opening(manu,0.001*manu.shape[0]*manu.shape[1])  # removal of small objects erroneously annotated (single pixels or little spots)
        manu = morphology.area_closing(manu,0.001*manu.shape[0]*manu.shape[1])  # removal of small holes errouneously not annotated

    #resizing
    img = img_as_ubyte(resize(img,[rsz,rsz]))
    manu = img_as_ubyte(resize(manu,[rsz,rsz]))
    manu[manu < 80] = 0
    manu[ (manu >= 80)*(manu <= 175) ] = 1
    manu[manu > 175] = 2

    # actual storage
    X_vl[n] = np.copy(img)
    Y_vl[n] = np.copy(manu)

# Y_vl = to_categorical(Y_vl, num_classes = NUM_CLASSES, dtype='float32')  # conversion to categorical data

# %whos

#print(vl_images[0],vl_images[1])

# SAVING PRE-PROCESSED

np.savez(os.path.join('drive/MyDrive/cytology challenge condivisa/01_PRE-PROCESSED',pre_proc_name),X_tr=X_tr,X_vl=X_vl)
pre_proc_annotations_name = 'IL1_manual_mask_' + str(rsz) + 'x' + str(rsz)  # <------------------------------------------------- comment this line if preprocessed annotations of wanted size are already existing
np.savez(os.path.join('drive/MyDrive/cytology challenge condivisa/01_PRE-PROCESSED',pre_proc_annotations_name),Y_tr=Y_tr,Y_vl=Y_vl)  # <-- comment this line if preprocessed annotations of wanted size are already existing