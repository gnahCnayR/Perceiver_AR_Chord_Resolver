#@title Install all dependencies (run only once per session)

#@title Import all needed modules

print('Loading needed modules. Please wait...')
import os
import random
import copy
import math
from collections import OrderedDict

from tqdm.notebook import tqdm

import matplotlib.pyplot as plt

import torch
from torchsummary import summary

print('Loading core modules...')
os.chdir('/content/Perceiver-Music-Transformer')

import TMIDIX

from perceiver_ar_pytorch import PerceiverAR
from autoregressive_wrapper import AutoregressiveWrapper

from midi2audio import FluidSynth
from IPython.display import Audio, display

os.chdir('/content/')
print('Done!')

"""# (DOWNLOAD MODEL)"""

#@title Download Perceiver Pre-Trained Solo Piano Model
# wget --no-check-certificate -O 'Perceiver-Solo-Piano-Model.pth' "https://onedrive.live.com/download?cid=8A0D502FC99C608F&resid=8A0D502FC99C608F%2118753&authkey=AMmtup34-lfGqyA"

"""# (LOAD)"""

#@title Load/Reload the model

full_path_to_model_checkpoint = "/content/Perceiver-Solo-Piano-Model.pth" #@param {type:"string"}

print('Loading the model...')
# Load model

# constants

SEQ_LEN = 4096 * 4 # Total of 16k
PREFIX_SEQ_LEN = (4096 * 4) - 1024 # 15.3k

model = PerceiverAR(
    num_tokens = 512,
    dim = 1024,
    depth = 24,
    heads = 16,
    dim_head = 64,
    cross_attn_dropout = 0.5,
    max_seq_len = SEQ_LEN,
    cross_attn_seq_len = PREFIX_SEQ_LEN
)
model = AutoregressiveWrapper(model)
model.cuda()

state_dict = torch.load(full_path_to_model_checkpoint)

model.load_state_dict(state_dict)

model.eval()

print('Done!')

# Model stats
summary(model)

"""# (GENERATE)

# Continuation
"""

#@title Load Seed/Custom MIDI
full_path_to_custom_MIDI_file = "/content/Perceiver-Music-Transformer/Perceiver-Piano-Seed-1.mid" #@param {type:"string"}

print('Loading custom MIDI file...')
score = TMIDIX.midi2ms_score(open(full_path_to_custom_MIDI_file, 'rb').read())

events_matrix = []

itrack = 1

#==================================================

# Memories augmentator

def augment(inputs):

  outs = []
  outy = []

  for i in range(1, 12):

    out1 = []
    out2 = []

    for j in range(0, len(inputs), 4):
      note = inputs[j:j+4]
      aug_note1 = copy.deepcopy(note)
      aug_note2 = copy.deepcopy(note)
      aug_note1[2] += i
      aug_note2[2] -= i

      out1.append(aug_note1)
      out2.append(aug_note2)

    outs.append(out1[random.randint(0, int(len(out1) / 2)):random.randint(int(len(out1) / 2), len(out1))])
    outs.append(out2[random.randint(0, int(len(out2) / 2)):random.randint(int(len(out2) / 2), len(out2))])

  for i in range(64):
    outy.extend(random.choice(outs))

  outy1 = []
  for o in outy:
    outy1.extend(o)

  return outy1

#==================================================

while itrack < len(score):
    for event in score[itrack]:         
        if event[0] == 'note' and event[3] != 9:
            events_matrix.append(event)
    itrack += 1

if len(events_matrix) > 0:

    # Sorting...
    events_matrix.sort(key=lambda x: x[4], reverse=True)
    events_matrix.sort(key=lambda x: x[1])

    # recalculating timings
    for e in events_matrix:
        e[1] = int(e[1] / 10)
        e[2] = int(e[2] / 20)

    # final processing...
    inputs = []
    
    inputs.extend([126+0, 126+128, 0+256, 0+384]) # Intro/Zero sequence

    pe = events_matrix[0]
    for e in events_matrix:

        time = max(0, min(126, e[1]-pe[1]))
        dur = max(1, min(126, e[2]))

        ptc = max(1, min(126, e[4]))
        vel = max(1, min(126, e[5]))

        inputs.extend([time+0, dur+128, ptc+256, vel+384])

        pe = e

# =================================

out1 = inputs

if len(out1) != 0:
    
    song = out1
    song_f = []
    time = 0
    dur = 0
    vel = 0
    pitch = 0
    channel = 0

    son = []

    song1 = []

    for s in song:
      if s > 127:
        son.append(s)

      else:
        if len(son) == 4:
          song1.append(son)
        son = []
        son.append(s)
    
    for s in song1:

        channel = 0 # Piano

        time += s[0] * 10
            
        dur = (s[1]-128) * 20
        
        pitch = (s[2]-256)

        vel = (s[3]-384)

        if pitch != 0:
                                  
          song_f.append(['note', time, dur, channel, pitch, vel ])

    detailed_stats = TMIDIX.Tegridy_SONG_to_MIDI_Converter(song_f,
                                                        output_signature = 'Perceiver',  
                                                        output_file_name = '/content/Perceiver-Music-Composition', 
                                                        track_name='Project Los Angeles',
                                                        list_of_MIDI_patches=[0, 24, 32, 40, 42, 46, 56, 71, 73, 0, 53, 19, 0, 0, 0, 0],
                                                        number_of_ticks_per_quarter=500)

    print('Done!')

print('Displaying resulting composition...')
fname = '/content/Perceiver-Music-Composition'

x = []
y =[]
c = []

colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver']

for s in song_f:
  x.append(s[1] / 1000)
  y.append(s[4])
  c.append(colors[s[3]])

FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
display(Audio(str(fname + '.wav'), rate=16000))

plt.figure(figsize=(14,5))
ax=plt.axes(title=fname)
ax.set_facecolor('black')

plt.scatter(x,y, c=c)
plt.xlabel("Time")
plt.ylabel("Pitch")
plt.show()

"""# Continuation"""

#@title Single Continuation Block Generator

#@markdown NOTE: Play with the settings to get different results
number_of_prime_tokens = 512 #@param {type:"slider", min:256, max:1020, step:4}
number_of_tokens_to_generate = 512 #@param {type:"slider", min:64, max:512, step:32}
temperature = 0.8 #@param {type:"slider", min:0.1, max:1, step:0.1}

#===================================================================
print('=' * 70)
print('Perceiver Music Model Continuation Generator')
print('=' * 70)

print('Generation settings:')
print('=' * 70)
print('Number of prime tokens:', number_of_prime_tokens)
print('Number of tokens to generate:', number_of_tokens_to_generate)
print('Model temperature:', temperature)

print('=' * 70)
print('Generating...')

# inp = augment(inputs)

inp = inputs * math.ceil((4096 * 4) / len(inputs))

inp = inp[:(4096 * 4)]

inp = inp[(512+len(inputs[:number_of_prime_tokens])):] + inputs[:number_of_prime_tokens]

inp = torch.LongTensor(inp).cuda()

out = model.generate(inp[None, ...], 
                     number_of_tokens_to_generate, 
                     temperature=temperature)  

out1 = out.cpu().tolist()[0]

if len(out1) != 0:
    
    song = inputs[:number_of_prime_tokens] + out1
    song_f = []
    time = 0
    dur = 0
    vel = 0
    pitch = 0
    channel = 0

    son = []

    song1 = []

    for s in song:
      if s > 127:
        son.append(s)

      else:
        if len(son) == 4:
          song1.append(son)
        son = []
        son.append(s)
    
    for s in song1:

        channel = 0 # Piano

        time += s[0] * 10
            
        dur = (s[1]-128) * 20
        
        pitch = (s[2]-256)

        vel = (s[3]-384)

        if pitch != 0:
                                  
          song_f.append(['note', time, dur, channel, pitch, vel ])

    detailed_stats = TMIDIX.Tegridy_SONG_to_MIDI_Converter(song_f,
                                                        output_signature = 'Perceiver',  
                                                        output_file_name = '/content/Perceiver-Music-Composition', 
                                                        track_name='Project Los Angeles',
                                                        list_of_MIDI_patches=[0, 24, 32, 40, 42, 46, 56, 71, 73, 0, 53, 19, 0, 0, 0, 0],
                                                        number_of_ticks_per_quarter=500)

    print('Done!')

print('Displaying resulting composition...')
fname = '/content/Perceiver-Music-Composition'

x = []
y =[]
c = []

colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver']

for s in song_f:
  x.append(s[1] / 1000)
  y.append(s[4])
  c.append(colors[s[3]])

FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
display(Audio(str(fname + '.wav'), rate=16000))

plt.figure(figsize=(14,5))
ax=plt.axes(title=fname)
ax.set_facecolor('black')

plt.scatter(x,y, c=c)
plt.xlabel("Time")
plt.ylabel("Pitch")
plt.show()

#@title Auto-Continue Custom MIDI

number_of_continuation_notes = 100 #@param {type:"slider", min:10, max:500, step:10}
number_of_prime_tokens = 256 #@param {type:"slider", min:64, max:512, step:4}
temperature = 0.8 #@param {type:"slider", min:0.1, max:1, step:0.1}

#===================================================================
print('=' * 70)
print('Perceiver Music Model Auto-Continuation Generator')
print('=' * 70)

print('Generation settings:')
print('=' * 70)
print('Number of continuation notes:', number_of_continuation_notes)
print('Number of prime tokens:', number_of_prime_tokens)
print('Model temperature:', temperature)

print('=' * 70)
print('Generating...')

out2 = copy.deepcopy(inputs[:number_of_prime_tokens])

# aug_inp = augment(inputs)

for i in tqdm(range(number_of_continuation_notes)):

  # inp = copy.deepcopy(aug_inp)

  inp = inputs * math.ceil((4096 * 4) / len(inputs))

  inp = inp[:(4096 * 4)]

  inp = inp[(512+len(out2)):] + out2

  inp1 = torch.LongTensor(inp).cuda()

  out = model.generate(inp1[None, ...], 
                      4, 
                      temperature=temperature)  

  out1 = out.cpu().tolist()[0]
  out2.extend(out1)

if len(out2) != 0:
    
    song = out2
    song_f = []
    time = 0
    dur = 0
    vel = 0
    pitch = 0
    channel = 0

    son = []

    song1 = []

    for s in song:
      if s > 127:
        son.append(s)

      else:
        if len(son) == 4:
          song1.append(son)
        son = []
        son.append(s)
    
    for s in song1:

        channel = 0 # Piano

        time += s[0] * 10
            
        dur = (s[1]-128) * 20
        
        pitch = (s[2]-256)

        vel = (s[3]-384)

        if pitch != 0:
                                  
          song_f.append(['note', time, dur, channel, pitch, vel ])

    detailed_stats = TMIDIX.Tegridy_SONG_to_MIDI_Converter(song_f,
                                                        output_signature = 'Perceiver',  
                                                        output_file_name = '/content/Perceiver-Music-Composition', 
                                                        track_name='Project Los Angeles',
                                                        list_of_MIDI_patches=[0, 24, 32, 40, 42, 46, 56, 71, 73, 0, 53, 19, 0, 0, 0, 0],
                                                        number_of_ticks_per_quarter=500)

    print('Done!')

print('Displaying resulting composition...')
fname = '/content/Perceiver-Music-Composition'

x = []
y =[]
c = []

colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver']

for s in song_f:
  x.append(s[1] / 1000)
  y.append(s[4])
  c.append(colors[s[3]])

FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
display(Audio(str(fname + '.wav'), rate=16000))

plt.figure(figsize=(14,5))
ax=plt.axes(title=fname)
ax.set_facecolor('black')

plt.scatter(x,y, c=c)
plt.xlabel("Time")
plt.ylabel("Pitch")
plt.show()

"""# Congrats! You did it! :)"""