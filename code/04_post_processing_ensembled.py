# -*- coding: utf-8 -*-
"""04_post_processing_ensembled.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mZMpqpTg2vY5W8OY2IqDgZiAGY9g8ves

***
***INSTALLINGS AND IMPORTINGS***
***

* Installings
"""

# INSTALLINGS

!pip install plotly==5.3.1
!pip install imagecodecs

"""* Importings"""

from google.colab import drive
drive.mount('/content/drive')

import os
import random
import numpy as np
import plotly.express as px
import imagecodecs
import cv2
import scipy


from skimage import measure, morphology
from scipy import ndimage
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from matplotlib import pyplot as plt
from tqdm import tqdm
from skimage.io import imread, imshow, imsave
from skimage.transform import resize
from skimage.segmentation import mark_boundaries
from skimage import img_as_ubyte
from skimage.morphology import binary_dilation, remove_small_objects, remove_small_holes,binary_closing,binary_opening
from math import sqrt,pi as pi

"""* Loading data in Colab"""

# DATA UNRAR AND INDAGATED HEATMAP SETTING

!pip install unrar

# manual masks
!unrar x "/content/drive/MyDrive/cytology challenge condivisa/00_DATASET/train.rar"        # unraring training set
!unrar x "/content/drive/MyDrive/cytology challenge condivisa/00_DATASET/validation.rar"   # unraring validation set
!unrar x "/content/drive/MyDrive/cytology challenge condivisa/00_DATASET/test.rar"         # unraring test set

# indagated net

current_net1 = 'DN_NORM_MAG1'
current_net2 = 'DN_NORM_IL7'
current_net3 = 'DN_NORM_IL8'

!unrar x "/content/drive/MyDrive/cytology challenge condivisa/03_PREDICTED/DN_NORM_MAG1.rar"  # unraring predictions
!unrar x "/content/drive/MyDrive/cytology challenge condivisa/03_PREDICTED/DN_NORM_IL7.rar"  # unraring predictions
!unrar x "/content/drive/MyDrive/cytology challenge condivisa//03_PREDICTED/DN_NORM_IL8.rar"  # unraring predictions

"""***
# ***OBTAINING MASKS***
***
"""

# CREATING DIRECTORIES IN WHICH TO STORE THE PREDICTED MASKS

# masks

path_predicted_tr_m = os.path.join(current_net1,"train","mask")
if not os.path.exists(path_predicted_tr_m):
  os.mkdir(path_predicted_tr_m)

path_predicted_vl_m = os.path.join(current_net1,"validation","mask")
if not os.path.exists(path_predicted_vl_m):
  os.mkdir(path_predicted_vl_m)

path_predicted_ts_m = os.path.join(current_net1,"test","mask")
if not os.path.exists(path_predicted_ts_m):
  os.mkdir(path_predicted_ts_m)

"""***
SIMPLE THRESHOLDING + WATERSHED (watershed trasform to separate adjacent/overlapping cells) + MORPHOLOGICAL REFINEMENT OPERATIONS
***

* Training set
"""

# TRAINING SET

# # creating directory for masks predicted with simple thresholding + whatershed method
# path_predicted_tr_m_curr = os.path.join(current_net1,"train","mask","simple thresholding")
# if not os.path.exists(path_predicted_tr_m_curr):
#   os.mkdir(path_predicted_tr_m_curr)

# path
tr_MANU_path = os.path.join('train','manual')  # path to manual annotations
tr_HM1_path = os.path.join(current_net1,'train','prob_map') # path to predicted heatmaps
tr_HM2_path = os.path.join(current_net2,'train','prob_map') # path to predicted heatmaps
tr_HM3_path = os.path.join(current_net3,'train','prob_map') # path to predicted heatmaps


# extracting list of all predicted heatmaps
tr_images = sorted(os.listdir(tr_HM1_path))


# body
perf_tr = np.zeros((1,3))  # for implementation convenience an a 0-performance row is initialized, it will be removed before showing performances
missed_cells_tr = []  # not found cells
erroneous_cells_tr = []  # "invented" cells
dinofcep_tr = []  # difference in the number of cells for each patch
for id_ in tqdm(tr_images, total=len(tr_images)):  # loop on all patches of training set

    manu = imagecodecs.imread(tr_MANU_path+'/'+id_)  # N-D image containing manual segmentations (each layer a different MM cell, 128 = cytoplasm | 255 = nucleus)
    # loading heatmap computed by the trained model
    hm1 = imread(tr_HM1_path+'/'+id_)
    hm2 = imread(tr_HM2_path+'/'+id_)
    hm3 = imread(tr_HM3_path+'/'+id_)
    hm = hm1 + hm2 +hm3

    # thresholding
    mask0 = np.zeros((hm.shape[1],hm.shape[2]),dtype=np.uint8)
    mask0[hm[0,:,:,1]>1.35] = 128
    mask0[hm[0,:,:,2]>1.35] = 255  # predictions on nuclei are more accurate in terms of edges, so it is ok to eventually overwrite cytoplasm segmentations w/ nucleus segmentation

    # morphological refinement operations
    mask0 = morphology.area_closing(mask0,area_threshold=200)  # small holes removal
    mask0 = morphology.area_opening(mask0,area_threshold=100)  # small objects removal
    #cyto = np.zeros_like(mask0,dtype = bool); cyto[mask0==128] = True; cyto = morphology.binary_dilation(cyto,morphology.disk(3)); mask0[cyto*~(mask0==255)] = 128  # little dilation of cytoplasms: this is needed to merge nuclei and cytoplasms and so best perform subsequent watershading
    #nucl = np.zeros_like(mask0,dtype = bool); nucl[mask0==255] = True; nucl = morphology.binary_dilation(nucl,morphology.disk(1)); mask0[nucl] = 255  # little dilation and smoothing of nuclei

    # resizing to original shape
    mask0 = img_as_ubyte(resize(mask0,(manu.shape[0],manu.shape[1])))
    mask0[mask0<80] = 0
    mask0[(mask0>=80)*(mask0<=175)] = 128
    mask0[mask0>175] = 255
    #mask0 = morphology.area_opening(mask0,0.005*mask0.shape[0]*mask0.shape[1])  # removal of too small objects and artifacts coming from resizing (during masks resizing unwanted upsampling artifacts can occur)
    # removal of too small nuclei
    nuclei,_ = ndimage.label(mask0==255)
    for n in range(1,nuclei.max()+1):
      if (nuclei==n).sum() < 0.003*mask0.shape[0]*mask0.shape[1]: mask0[nuclei==n] = 0


    # eventual watershed (hypothesis of each cytoplasm being connected to
    # corresponding nuclues in at leat 1 pixel is done) and storing each
    #segmented cell on different layers
    mask = np.zeros((mask0.shape[0],mask0.shape[1],1),dtype=np.uint8)  # for implementation convenience an empty layer is initialized, it will be removed before saving the final N-layer mask
    labeled, n_trees = ndimage.label((mask0==128)+(mask0==255))  # finding connected components of thresholded mask
    for i in range(1,n_trees+1):
      _,n_nuc = ndimage.label((labeled==i)*(mask0==255))  # finding number of nuclei in the currently passed connected component (CC)
      if n_nuc > 1:   # case in which there is than 1 nucleus in the current CC, then the CC may be a cluster of cells --> watersheding is applied
        dist_transform = ndimage.distance_transform_edt(labeled==i)  # distance transform of the CC
        dst_for_mark = ndimage.distance_transform_edt((labeled==i)*(mask0==255)) # distance trasform on nuclei of the CC
        lab_for_mark,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling nuclei of the CC
        mark_coords = peak_local_max(dst_for_mark, labels=lab_for_mark, num_peaks_per_label=1)  # finding markers' coordinate for subsequent watershed
        markers = np.zeros(dist_transform.shape, dtype=bool); markers[tuple(mark_coords.T)] = True; markers, _ = ndimage.label(markers)  # markers
        separated = watershed(-dist_transform, markers, mask=labeled==i)  # actual watersheding

        restore = False  # nuclei restoring flag
        for j in range(1,separated.max()+1):  # cycling on the identified cells of the cluster
          curr = np.zeros_like(mask0); curr[separated==j] = mask0[separated==j] # segmentation of current cell
          mask = np.append(mask,curr[:,:,np.newaxis],axis=2)
          # checking if nuclei restoring is needed (watersheding could have
          # -erroneously- cut some nucleus)
          _,n_nuc2 = ndimage.label(curr==255)
          if n_nuc2 > 1: restore = True

        # restoring initial nuclei
        if restore:
          rank = np.zeros((n_nuc,n_nuc))  # array that will contain ranking of appartenence for each nuclei (on columns) to each watersheded object
          CCC_nuc_lab,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling current cluster's (pre watershed) nuclei
          # actual ranking
          for k in range(1,n_nuc+1):  # loop over nuclei
             for l in range(1,n_nuc+1):  # loop over watersheded objects
               rank[l-1,k-1] = ((CCC_nuc_lab==k)*(mask[:,:,-l]==255)).sum()/(CCC_nuc_lab==k).sum()
          rank = np.argmax(rank,0)+1  # array containing for each nucleus the watersheded object containing it at greatest %
          # actual restoring
          for k in range(n_nuc):
            mask[CCC_nuc_lab==k+1,-rank[k]] = 255
            mask[CCC_nuc_lab==k+1,-1:-rank[k]:-1] = 0; mask[CCC_nuc_lab==k+1,-rank[k]-1:-n_nuc-1:-1] = 0;

      else:  # case in which watersheding is not needed
        curr = np.zeros_like(mask0); curr[labeled==i] = mask0[labeled==i] # segmentation of current cell
        mask = np.append(mask,curr[:,:,np.newaxis],axis=2)

    # removing layers in which no nucleus has been found (minimum requirement to
    # have a segmentation is presence of nucleus), with this step also initial
    # empty layer initialization is removed
    w2m = np.sum(mask==255,axis=(0,1)).astype(bool); mask = mask[:,:,w2m]

    # if no cells have been segmneted, an empty single layer mask is saved [2-D
    # empty mask], else if only one cell has been found, then the mask is
    # "compressed" to 2-D
    if mask.size == 0:  # no cell case
      mask = np.zeros((mask0.shape[0],mask0.shape[1]),dtype=np.uint8)
    elif mask.shape[2] == 1:  # 1 cell case
      mask = np.squeeze(mask)

    # saving mask: please, to read automatic annotations use 'imread' method of
    # skimage library and not the one of imagecodecs library
    # imsave(os.path.join(path_predicted_tr_m_curr,id_),mask,check_contrast=False)


    # calculating performances at single-cell mask level: please notice in this
    # implementation intersection over union (IoU) at whole cell level has been
    # used to match manual single layer mask with its correspective automatic
    # mask in order to calculate performances (IoU nucleus, IoU cytoplasm, IoU
    # whole cell)

    # defining number of layers of manual mask and automatic mask
    try:
      n_layer_manu = manu.shape[2]
    except:  # case in which no cells or only 1 cell has been segmented
      if manu.sum()==0:  # no found cell case
        n_layer_manu = 0
      else:  # one cell case
        n_layer_manu = 1
        manu = np.expand_dims(manu,2)  # dimensions expansion is needed to mantain a unificate code also in case of only 1 cell segmentation
    try:
      n_layer_auto = mask.shape[2]
    except:  # case in which no cells or only 1 cell has been segmented
      if mask.sum()==0:  # no found cell case
        n_layer_auto = 0
      else:  # one cell case
        n_layer_auto = 1
        mask = np.expand_dims(mask,2)  # dimensions expansion is needed to mantain a unificate code also in case of only 1 cell segmentation

    perf = np.zeros((max(n_layer_manu,n_layer_auto),3))  # array that will contain performances for the current patch mask predictions
    if n_layer_manu and n_layer_auto:  # if at least one cell has been segmented in both manual mask and automatic mask
      IoU_WC = np.zeros((n_layer_auto,n_layer_manu))  # array that will contain IoU of whole cell all possible combinations of 'single layer manual mask' | 'single layer predicted mask'
      # whole cell level IoU of all possible combinations
      for o1 in range(n_layer_manu):
        for o2 in range(n_layer_auto):
          IoU_WC[o2,o1] = ((manu[:,:,o1]).astype(bool)*(mask[:,:,o2]).astype(bool)).sum()/((manu[:,:,o1]).astype(bool)+(mask[:,:,o2]).astype(bool)).sum()  #IoU of current combination
      # case in which automatic prediction found at least equal number of cells of
      # those identified in the manual annotations
      if n_layer_auto >= n_layer_manu:
        order = np.argmax(IoU_WC,axis=0)  # finding most matching automatically segmented cell mask for each manually segmented cell
        # solving manual mask --> automatic mask matching redundancies: it may happen that one single-cell segmetation of one of the two types is matched with more than one single-cell segmentation of the other type, but obviously matchings have to be non redundant
        _,inv_ind,counts = np.unique(order,return_inverse=True, return_counts=True)
        if (counts>1).any():
          for a in range(max(inv_ind)+1):
            if (inv_ind==a).sum() > 1:
              w2d = (inv_ind==a)*~(IoU_WC.max(axis=0)==max(IoU_WC.max(axis=0)[inv_ind==a]))
              order = np.delete(order,w2d)
              inv_ind = np.delete(inv_ind,w2d)
              IoU_WC = np.delete(IoU_WC,w2d,1)
              manu = manu[:,:,~w2d]
        IoU_WC = np.max(IoU_WC,axis=0);  # IoU whole cell for all matched cell pairs
        IoU_N = np.sum((manu==255)*(mask[:,:,order]==255),axis=(0,1))/np.sum((manu==255)+(mask[:,:,order]==255),axis=(0,1))  # IoU nucleus for all matched cell pairs
        IoU_C = np.sum((manu==128)*(mask[:,:,order]==128),axis=(0,1))/np.sum((manu==128)+(mask[:,:,order]==128),axis=(0,1))  # IoU cytoplasm for all matched cell pairs
      # case in which automatic prediction found a smaller number of cells of
      # those identified in the manual annotations
      else:
        order = np.argmax(IoU_WC,axis=1)
        _,inv_ind,counts = np.unique(order,return_inverse=True, return_counts=True)
        if (counts>1).any():
          w2m_WC = np.ones(len(order),dtype=bool)
          for a in range(max(inv_ind)+1):
            if (inv_ind==a).sum() > 1:
              w2d = (inv_ind==a)*~(IoU_WC.max(axis=1)==max(IoU_WC.max(axis=1)[inv_ind==a]))
              order = np.delete(order,w2d)
              inv_ind = np.delete(inv_ind,w2d)
              IoU_WC = np.delete(IoU_WC,w2d,0)
              mask = mask[:,:,~w2d]
        IoU_WC = np.max(IoU_WC,axis=1)
        IoU_N = np.sum((manu[:,:,order]==255)*(mask==255),axis=(0,1))/np.sum((manu[:,:,order]==255)+(mask==255),axis=(0,1))
        IoU_C = np.sum((manu[:,:,order]==128)*(mask==128),axis=(0,1))/np.sum((manu[:,:,order]==128)+(mask==128),axis=(0,1))
      perf[:min(manu.shape[2],mask.shape[2]),:] = np.stack((IoU_N.T,IoU_C.T,IoU_WC.T),axis=1)  # performances on unmatched cells are automatically set to 0 by the previious initialization of array
    perf_tr = np.concatenate((perf_tr,perf),axis=0)  # adding current patch performances to global ones
    erroneous_cells_tr.append(n_layer_auto-(perf[:,0]>0.1).sum())
    missed_cells_tr.append(n_layer_manu-(perf[:,0]>0.1).sum())
    dinofcep_tr.append(abs(n_layer_manu-n_layer_auto))

perf_tr = perf_tr[1:,:]  # removing convenience initialization from array
cell_number_diff_tr = np.array((erroneous_cells_tr,missed_cells_tr,dinofcep_tr),dtype=np.int8).T


# performances printing
print(f"\nPERFORMNACES ON TRAINING SET as IoU nuclei | IoU cytoplasm | IoU whole cell:\n{perf_tr}\n\nmean and std: {np.mean(perf_tr,axis=0)} and {np.std(perf_tr,axis=0)}")
print(f"\n\n\n\nINVENTED CELLS | MISSED CELLS | DIFFERENCE IN # OF SEGMNETED CELLS:\n\n{cell_number_diff_tr}\n\n mean: {np.mean(cell_number_diff_tr,axis=0)}")

"""* Validation set"""

# VALIDATION SET

# # creating directory for masks predicted with simple thresholding + whatershed method
# path_predicted_vl_m_curr = os.path.join(current_net1,"validation","mask","simple thresholding")
# if not os.path.exists(path_predicted_vl_m_curr):
#   os.mkdir(path_predicted_vl_m_curr)

# path
vl_MANU_path = os.path.join('validation','manual')  # path to manual annotations
vl_HM1_path = os.path.join(current_net1,'validation','prob_map') # path to predicted heatmaps of net1
vl_HM2_path = os.path.join(current_net2,'validation','prob_map') # path to predicted heatmaps of net2
vl_HM3_path = os.path.join(current_net3,'validation','prob_map') # path to predicted heatmaps of net3


# extracting list of all predicted heatmaps
vl_images = sorted(os.listdir(vl_HM1_path))


# body
perf_vl = np.zeros((1,3))  # for implementation convenience an a 0-performance row is initialized, it will be removed before showing performances
missed_cells_vl = []  # not found cells
erroneous_cells_vl = []  # "invented" cells
dinofcep_vl = []  # difference in the number of cells for each patch
for n, id_ in tqdm(enumerate(vl_images), total=len(vl_images)):  # loop on all patches of training set

    manu = imagecodecs.imread(vl_MANU_path+'/'+id_)  # N-D image containing manual segmentations (each layer a different MM cell, 128 = cytoplasm | 255 = nucleus)
    # loading heatmap computed by the trained model
    hm1 = imread(vl_HM1_path+'/'+id_)
    hm2 = imread(vl_HM2_path+'/'+id_)
    hm3 = imread(vl_HM3_path+'/'+id_)
    hm = hm1 + hm2 + hm3

    # thresholding
    mask0 = np.zeros((hm.shape[1],hm.shape[2]),dtype=np.uint8)
    mask0[hm[0,:,:,1]>1.35] = 128
    mask0[hm[0,:,:,2]>1.35] = 255  # predictions on nuclei are more accurate in terms of edges, so it is ok to eventually overwrite cytoplasm segmentations w/ nucleus segmentation

    # morphological refinement operations
    mask0 = morphology.area_closing(mask0,area_threshold=200)  # small holes removal
    mask0 = morphology.area_opening(mask0,area_threshold=100)  # small objects removal
    #cyto = np.zeros_like(mask0,dtype = bool); cyto[mask0==128] = True; cyto = morphology.binary_dilation(cyto,morphology.disk(3)); mask0[cyto*~(mask0==255)] = 128  # little dilation of cytoplasms: this is needed to merge nuclei and cytoplasms and so best perform subsequent watershading
    #nucl = np.zeros_like(mask0,dtype = bool); nucl[mask0==255] = True; nucl = morphology.binary_dilation(nucl,morphology.disk(1)); mask0[nucl] = 255  # little dilation and smoothing of nuclei

    # resizing to original shape
    mask0 = img_as_ubyte(resize(mask0,(manu.shape[0],manu.shape[1])))
    mask0[mask0<80] = 0
    mask0[(mask0>=80)*(mask0<=175)] = 128
    mask0[mask0>175] = 255
    #mask0 = morphology.area_opening(mask0,0.005*mask0.shape[0]*mask0.shape[1])  # removal of too small objects and artifacts coming from resizing (during masks resizing unwanted upsampling artifacts can occur)
    # removal of too small nuclei
    nuclei,_ = ndimage.label(mask0==255)
    for n in range(1,nuclei.max()+1):
      if (nuclei==n).sum() < 0.004*mask0.shape[0]*mask0.shape[1]: mask0[nuclei==n] = 0


    # eventual watershed (hypothesis of each cytoplasm being connected to
    # corresponding nuclues in at leat 1 pixel is done) and storing each
    #segmented cell on different layers
    mask = np.zeros((mask0.shape[0],mask0.shape[1],1),dtype=np.uint8)  # for implementation convenience an empty layer is initialized, it will be removed before saving the final N-layer mask
    labeled, n_trees = ndimage.label((mask0==128)+(mask0==255))  # finding connected components of thresholded mask
    for i in range(1,n_trees+1):
      _,n_nuc = ndimage.label((labeled==i)*(mask0==255))  # finding number of nuclei in the currently passed connected component (CC)
      if n_nuc > 1:   # case in which there is than 1 nucleus in the current CC, then the CC may be a cluster of cells --> watersheding is applied
        dist_transform = ndimage.distance_transform_edt(labeled==i)  # distance transform of the CC
        dst_for_mark = ndimage.distance_transform_edt((labeled==i)*(mask0==255)) # distance trasform on nuclei of the CC
        lab_for_mark,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling nuclei of the CC
        mark_coords = peak_local_max(dst_for_mark, labels=lab_for_mark, num_peaks_per_label=1)  # finding markers' coordinate for subsequent watershed
        markers = np.zeros(dist_transform.shape, dtype=bool); markers[tuple(mark_coords.T)] = True; markers, _ = ndimage.label(markers)  # markers
        separated = watershed(-dist_transform, markers, mask=labeled==i)  # actual watersheding

        restore = False  # nuclei restoring flag
        for j in range(1,separated.max()+1):  # cycling on the identified cells of the cluster
          curr = np.zeros_like(mask0); curr[separated==j] = mask0[separated==j] # segmentation of current cell
          mask = np.append(mask,curr[:,:,np.newaxis],axis=2)
          # checking if nuclei restoring is needed (watersheding could have
          # -erroneously- cut some nucleus)
          _,n_nuc2 = ndimage.label(curr==255)
          if n_nuc2 > 1: restore = True

        # restoring initial nuclei
        if restore:
          rank = np.zeros((n_nuc,n_nuc))  # array that will contain ranking of appartenence for each nuclei (on columns) to each watersheded object
          CCC_nuc_lab,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling current cluster's (pre watershed) nuclei
          # actual ranking
          for k in range(1,n_nuc+1):  # loop over nuclei
             for l in range(1,n_nuc+1):  # loop over watersheded objects
               rank[l-1,k-1] = ((CCC_nuc_lab==k)*(mask[:,:,-l]==255)).sum()/(CCC_nuc_lab==k).sum()
          rank = np.argmax(rank,0)+1  # array containing for each nucleus the watersheded object containing it at greatest %
          # actual restoring
          for k in range(n_nuc):
            mask[CCC_nuc_lab==k+1,-rank[k]] = 255
            mask[CCC_nuc_lab==k+1,-1:-rank[k]:-1] = 0; mask[CCC_nuc_lab==k+1,-rank[k]-1:-n_nuc-1:-1] = 0;

      else:  # case in which watersheding is not needed
        curr = np.zeros_like(mask0); curr[labeled==i] = mask0[labeled==i] # segmentation of current cell
        mask = np.append(mask,curr[:,:,np.newaxis],axis=2)

    # removing layers in which no nucleus has been found (minimum requirement to
    # have a segmentation is presence of nucleus), with this step also initial
    # empty layer initialization is removed
    w2m = np.sum(mask==255,axis=(0,1)).astype(bool); mask = mask[:,:,w2m]

    # if no cells have been segmneted, an empty single layer mask is saved [2-D
    # empty mask], else if only one cell has been found, then the mask is
    # "compressed" to 2-D
    if mask.size == 0:  # no cell case
      mask = np.zeros((mask0.shape[0],mask0.shape[1]),dtype=np.uint8)
    elif mask.shape[2] == 1:  # 1 cell case
      mask = np.squeeze(mask)

    # saving mask: please, to read automatic annotations use 'imread' method of
    # skimage library and not the one of imagecodecs library
    # imsave(os.path.join(path_predicted_vl_m_curr,id_),mask,check_contrast=False)


    # calculating performances at single-cell mask level: please notice in this
    # implementation intersection over union (IoU) at whole cell level has been
    # used to match manual single layer mask with its correspective automatic
    # mask in order to calculate performances (IoU nucleus, IoU cytoplasm, IoU
    # whole cell)

    # defining number of layers of manual mask and automatic mask
    try:
      n_layer_manu = manu.shape[2]
    except:  # case in which no cells or only 1 cell has been segmented
      if manu.sum()==0:  # no found cell case
        n_layer_manu = 0
      else:  # one cell case
        n_layer_manu = 1
        manu = np.expand_dims(manu,2)  # dimensions expansion is needed to mantain a unificate code also in case of only 1 cell segmentation
    try:
      n_layer_auto = mask.shape[2]
    except:  # case in which no cells or only 1 cell has been segmented
      if mask.sum()==0:  # no found cell case
        n_layer_auto = 0
      else:  # one cell case
        n_layer_auto = 1
        mask = np.expand_dims(mask,2)  # dimensions expansion is needed to mantain a unificate code also in case of only 1 cell segmentation

    perf = np.zeros((max(n_layer_manu,n_layer_auto),3))  # array that will contain performances for the current patch mask predictions
    if n_layer_manu and n_layer_auto:  # if at least one cell has been segmented in both manual mask and automatic mask
      IoU_WC = np.zeros((n_layer_auto,n_layer_manu))  # array that will contain IoU of whole cell all possible combinations of 'single layer manual mask' | 'single layer predicted mask'
      # whole cell level IoU of all possible combinations
      for o1 in range(n_layer_manu):
        for o2 in range(n_layer_auto):
          IoU_WC[o2,o1] = ((manu[:,:,o1]).astype(bool)*(mask[:,:,o2]).astype(bool)).sum()/((manu[:,:,o1]).astype(bool)+(mask[:,:,o2]).astype(bool)).sum()  #IoU of current combination
      # case in which automatic prediction found at least equal number of cells of
      # those identified in the manual annotations
      if n_layer_auto >= n_layer_manu:
        order = np.argmax(IoU_WC,axis=0)  # finding most matching automatically segmented cell mask for each manually segmented cell
        # solving manual mask --> automatic mask matching redundancies: it may happen that one single-cell segmetation of one of the two types is matched with more than one single-cell segmentation of the other type, but obviously matchings have to be non redundant
        _,inv_ind,counts = np.unique(order,return_inverse=True, return_counts=True)
        if (counts>1).any():
          for a in range(max(inv_ind)+1):
            if (inv_ind==a).sum() > 1:
              w2d = (inv_ind==a)*~(IoU_WC.max(axis=0)==max(IoU_WC.max(axis=0)[inv_ind==a]))
              order = np.delete(order,w2d)
              inv_ind = np.delete(inv_ind,w2d)
              IoU_WC = np.delete(IoU_WC,w2d,1)
              manu = manu[:,:,~w2d]
        IoU_WC = np.max(IoU_WC,axis=0);  # IoU whole cell for all matched cell pairs
        IoU_N = np.sum((manu==255)*(mask[:,:,order]==255),axis=(0,1))/np.sum((manu==255)+(mask[:,:,order]==255),axis=(0,1))  # IoU nucleus for all matched cell pairs
        IoU_C = np.sum((manu==128)*(mask[:,:,order]==128),axis=(0,1))/np.sum((manu==128)+(mask[:,:,order]==128),axis=(0,1))  # IoU cytoplasm for all matched cell pairs
      # case in which automatic prediction found a smaller number of cells of
      # those identified in the manual annotations
      else:
        order = np.argmax(IoU_WC,axis=1)
        _,inv_ind,counts = np.unique(order,return_inverse=True, return_counts=True)
        if (counts>1).any():
          w2m_WC = np.ones(len(order),dtype=bool)
          for a in range(max(inv_ind)+1):
            if (inv_ind==a).sum() > 1:
              w2d = (inv_ind==a)*~(IoU_WC.max(axis=1)==max(IoU_WC.max(axis=1)[inv_ind==a]))
              order = np.delete(order,w2d)
              inv_ind = np.delete(inv_ind,w2d)
              IoU_WC = np.delete(IoU_WC,w2d,0)
              mask = mask[:,:,~w2d]
        IoU_WC = np.max(IoU_WC,axis=1)
        IoU_N = np.sum((manu[:,:,order]==255)*(mask==255),axis=(0,1))/np.sum((manu[:,:,order]==255)+(mask==255),axis=(0,1))
        IoU_C = np.sum((manu[:,:,order]==128)*(mask==128),axis=(0,1))/np.sum((manu[:,:,order]==128)+(mask==128),axis=(0,1))
      perf[:min(manu.shape[2],mask.shape[2]),:] = np.stack((IoU_N.T,IoU_C.T,IoU_WC.T),axis=1)  # performances on unmatched cells are automatically set to 0 by the previious initialization of array
    perf_vl = np.concatenate((perf_vl,perf),axis=0)  # adding current patch performances to global ones
    erroneous_cells_vl.append(n_layer_auto-(perf[:,0]>0.1).sum())
    missed_cells_vl.append(n_layer_manu-(perf[:,0]>0.1).sum())
    dinofcep_vl.append(abs(n_layer_manu-n_layer_auto))

perf_vl = perf_vl[1:,:]  # removing convenience initialization from array
cell_number_diff_vl = np.array((erroneous_cells_vl,missed_cells_vl,dinofcep_vl),dtype=np.int8).T


# performances printing
print(f"\n\n\nPERFORMNACES ON VALIDATION SET as IoU nuclei | IoU cytoplasm | IoU whole cell:\n\n{perf_vl}\n\nmean and std: {np.mean(perf_vl,axis=0)} and {np.std(perf_vl,axis=0)}")
print(f"\n\n\n\nINVENTED CELLS | MISSED CELLS | DIFFERENCE IN # OF SEGMNETED CELLS:\n\n{cell_number_diff_vl}\n\n mean: {np.mean(cell_number_diff_vl,axis=0)}")

"""* Test set"""

# TEST SET

# creating directory for masks predicted with simple thresholding + whatershed method
path_predicted_ts_m_curr = os.path.join(current_net1,"test","mask","simple thresholding")
if not os.path.exists(path_predicted_ts_m_curr):
  os.mkdir(path_predicted_ts_m_curr)

# path
ts_IMGS_path = os.path.join('test','images')  # path to manual annotations
ts_HM1_path = os.path.join(current_net1,'test','prob_map') # path to predicted heatmaps of net1
ts_HM2_path = os.path.join(current_net2,'test','prob_map') # path to predicted heatmaps of net2
ts_HM3_path = os.path.join(current_net3,'test','prob_map') # path to predicted heatmaps of net3

# extracting list of all predicted heatmaps
ts_images = os.listdir(ts_HM1_path)


# body
for id_ in tqdm(ts_images, total=len(ts_images)):  # loop on all patches of training set

    img = imread(ts_IMGS_path+'/'+id_) # uint8 stained image
    # loading heatmap computed by the trained model
    hm1 = imread(ts_HM1_path+'/'+id_)
    hm2 = imread(ts_HM2_path+'/'+id_)
    hm3 = imread(ts_HM3_path+'/'+id_)
    hm = hm1 + hm2 +hm3


    # thresholding
    mask0 = np.zeros((hm.shape[1],hm.shape[2]),dtype=np.uint8)
    mask0[hm[0,:,:,1]>0.5] = 128
    mask0[hm[0,:,:,2]>0.5] = 255  # predictions on nuclei are more accurate in terms of edges, so it is ok to eventually overwrite cytoplasm segmentations w/ nucleus segmentation

    # morphological refinement operations
    mask0 = morphology.area_closing(mask0)  # small holes removal
    mask0 = morphology.area_opening(mask0)  # small objects removal
    cyto = np.zeros_like(mask0,dtype = bool); cyto[mask0==128] = True; cyto = morphology.binary_dilation(cyto,morphology.disk(3)); mask0[cyto*~(mask0==255)] = 128  # little dilation of cytoplasms: this is needed to merge nuclei and cytoplasms and so best perform subsequent watershading
    nucl = np.zeros_like(mask0,dtype = bool); nucl[mask0==255] = True; nucl = morphology.binary_dilation(nucl,morphology.disk(1)); mask0[nucl] = 255  # little dilation and smoothing of nuclei

    # resizing to original shape
    mask0 = img_as_ubyte(resize(mask0,(manu.shape[0],manu.shape[1])))
    mask0[mask0<80] = 0
    mask0[(mask0>=80)*(mask0<=175)] = 128
    mask0[mask0>175] = 255
    mask0 = morphology.area_opening(mask0,0.005*mask0.shape[0]*mask0.shape[1])  # removal of too small objects and artifacts coming from resizing (during masks resizing unwanted upsampling artifacts can occur)
    # removal of too small nuclei
    nuclei,_ = ndimage.label(mask0==255)
    for n in range(1,nuclei.max()+1):
      if (nuclei==n).sum() < 0.005*mask0.shape[0]*mask0.shape[1]: mask0[nuclei==n] = 0


    # eventual watershed (hypothesis of each cytoplasm being connected to
    # corresponding nuclues in at leat 1 pixel is done) and storing each
    #segmented cell on different layers
    mask = np.zeros((mask0.shape[0],mask0.shape[1],1),dtype=np.uint8)  # for implementation convenience an empty layer is initialized, it will be removed before saving the final N-layer mask
    labeled, n_trees = ndimage.label((mask0==128)+(mask0==255))  # finding connected components of thresholded mask
    for i in range(1,n_trees+1):
      _,n_nuc = ndimage.label((labeled==i)*(mask0==255))  # finding number of nuclei in the currently passed connected component (CC)
      if n_nuc > 1:   # case in which there is than 1 nucleus in the current CC, then the CC may be a cluster of cells --> watersheding is applied
        dist_transform = ndimage.distance_transform_edt(labeled==i)  # distance transform of the CC
        dst_for_mark = ndimage.distance_transform_edt((labeled==i)*(mask0==255)) # distance trasform on nuclei of the CC
        lab_for_mark,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling nuclei of the CC
        mark_coords = peak_local_max(dst_for_mark, labels=lab_for_mark, num_peaks_per_label=1)  # finding markers' coordinate for subsequent watershed
        markers = np.zeros(dist_transform.shape, dtype=bool); markers[tuple(mark_coords.T)] = True; markers, _ = ndimage.label(markers)  # markers
        separated = watershed(-dist_transform, markers, mask=labeled==i)  # actual watersheding

        restore = False  # nuclei restoring flag
        for j in range(1,separated.max()+1):  # cycling on the identified cells of the cluster
          curr = np.zeros_like(mask0); curr[separated==j] = mask0[separated==j] # segmentation of current cell
          mask = np.append(mask,curr[:,:,np.newaxis],axis=2)
          # checking if nuclei restoring is needed (watersheding could have
          # -erroneously- cut some nucleus)
          _,n_nuc2 = ndimage.label(curr==255)
          if n_nuc2 > 1: restore = True

        # restoring initial nuclei
        if restore:
          rank = np.zeros((n_nuc,n_nuc))  # array that will contain ranking of appartenence for each nuclei (on columns) to each watersheded object
          CCC_nuc_lab,_ = ndimage.label((labeled==i)*(mask0==255))  # labeling current cluster's (pre watershed) nuclei
          # actual ranking
          for k in range(1,n_nuc+1):  # loop over nuclei
             for l in range(1,n_nuc+1):  # loop over watersheded objects
               rank[l-1,k-1] = ((CCC_nuc_lab==k)*(mask[:,:,-l]==255)).sum()/(CCC_nuc_lab==k).sum()
          rank = np.argmax(rank,0)+1  # array containing for each nucleus the watersheded object containing it at greatest %
          # actual restoring
          for k in range(n_nuc):
            mask[CCC_nuc_lab==k+1,-rank[k]] = 255
            mask[CCC_nuc_lab==k+1,-1:-rank[k]:-1] = 0; mask[CCC_nuc_lab==k+1,-rank[k]-1:-n_nuc-1:-1] = 0;

      else:  # case in which watersheding is not needed
        curr = np.zeros_like(mask0); curr[labeled==i] = mask0[labeled==i] # segmentation of current cell
        mask = np.append(mask,curr[:,:,np.newaxis],axis=2)

    # removing layers in which no nucleus has been found (minimum requirement to
    # have a segmentation is presence of nucleus), with this step also initial
    # empty layer initialization is removed
    w2m = np.sum(mask==255,axis=(0,1)).astype(bool); mask = mask[:,:,w2m]

    # if no cells have been segmneted, an empty single layer mask is saved [2-D
    # empty mask], else if only one cell has been found, then the mask is
    # "compressed" to 2-D
    if mask.size == 0:  # no cell case
      mask = np.zeros((mask0.shape[0],mask0.shape[1]),dtype=np.uint8)
    elif mask.shape[2] == 1:  # 1 cell case
      mask = np.squeeze(mask)

    # saving mask: please, to read automatic annotations use 'imread' method of
    # skimage library and not the one of imagecodecs library
    # imsave(os.path.join(path_predicted_ts_m_curr,id_),mask,check_contrast=False)

# PERFORMANCES PRINTING