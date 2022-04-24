# Change detection head

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.padding import ReplicationPad2d

def get_in_channels(feat_scales, inner_channel, channel_multiplier):
    '''
    Get the number of input layers to the change detection head.
    '''
    in_channels = 0
    for scale in feat_scales:
        if scale < 4: #256 x 256
            in_channels += inner_channel*channel_multiplier[0]
        elif scale < 6: #128 x 128
            in_channels += inner_channel*channel_multiplier[1]
        elif scale < 7: #64 x 64
            in_channels += inner_channel*channel_multiplier[1]
        elif scale < 10: #64 x 64
            in_channels += inner_channel*channel_multiplier[2]
        elif scale < 12: #32 x 32
            in_channels += inner_channel*channel_multiplier[3]
        elif scale < 15: #16 x 16
            in_channels += inner_channel*channel_multiplier[4]
        else:
            print('Unbounded number for feat_scales. 0<=feat_scales<=14') 
    return in_channels
    

class cd_head(nn.Module):
    '''
    Change detection head.
    '''

    def __init__(self, feat_scales, out_channels=2, inner_channel, channel_multiplier, img_size=256):
        super(cd_head, self).__init__()

        # Define the parameters of the change detection head
        self.feat_scales    = feat_scales
        self.in_channels    = get_in_channels(feat_scales, inner_channel, channel_multiplier)
        self.img_size       = img_size

        # Convolutional layers before parsing to difference head
        self.diff_layers = nn.ModuleList()
        for feat in feat_scales:
            self.diff_layers.append(nn.Conv2d(get_in_channels([feat]), get_in_channels([feat]), kernel_size=3, padding=1))

        #MLP layer to reduce the feature dimention
        self.conv1_final = nn.Conv2d(self.in_channels, 64, kernel_size=1, padding=0)

        #Get final change map
        self.conv2_final = nn.Conv2d(64, out_channels, kernel_size=3, padding=1)

        self.relu = torch.nn.ReLU()

    def forward(self, feats_A, feats_B):

        feats_diff = []
        c=0
        for layer in self.diff_layers:
            x = torch.abs(layer(feats_A[self.feat_scales[c]]) - layer(feats_B[self.feat_scales[c]]))
            feats_diff.append(x)
            c+=1
        
        c=0
        for i in range(0, len(feats_diff)):
            if feats_diff[i].size(2) != self.img_size:
                feat_diff_up = F.interpolate(feats_diff[i], size=(self.img_size, self.img_size), mode="bilinear")
            else:
                feat_diff_up = feats_diff[i]
            
            #Concatenating upsampled features to ''feats_diff_up''
            if c==0:
                feats_diff_up = feat_diff_up
                c+=1
            else:
                feats_diff_up = torch.cat((feats_diff_up, feat_diff_up), dim=1)

        cm = self.conv2_final(self.relu(self.conv1_final(feats_diff_up)))

        return cm

    