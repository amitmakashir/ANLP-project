# -*- coding: utf-8 -*-
"""Copy of Text-summarization.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MsR9qA3mfnKRf20-QwI5uomzJ3IQMsFU
"""


# Commented out IPython magic to ensure Python compatibility.
# Project Path
# %pwd
# %cd drive/My Drive/ANLP-Project/
# %pwd

isTrain = False
import tensorflow as tf
import numpy as np
import pandas as pd 
import re
import nltk
from bs4 import BeautifulSoup
from tensorflow.keras.preprocessing.text import Tokenizer 
from tensorflow.keras.preprocessing.sequence import pad_sequences
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from tensorflow.keras.layers import Input, LSTM, Embedding, Dense, Concatenate, TimeDistributed,Attention
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping
import warnings
import contractions
from sklearn.model_selection import train_test_split
pd.set_option("display.max_colwidth", 200)
# warnings.filterwarnings("ignore")

# Downloads
nltk.download('stopwords')
nltk.download('punkt')

assert(tf.__version__ == "2.0.0")

data_directory_path = "./Data/"
reviews_data = data_directory_path + "Reviews.csv"

reviews_df = pd.read_csv(reviews_data,nrows=100000)
# reviews_df = pd.read_csv(reviews_data)

data_df = reviews_df.filter(items=["Summary","Text"])
data_df.head()

data_df.drop_duplicates(subset=['Text'],inplace=True)#dropping duplicates
data_df.dropna(axis=0,inplace=True)#dropping na

data_df.info()

stop_words = set(stopwords.words('english'))

def clean_text(text_string, remove_stop_words=False):
    text_string = text_string.lower()
    tokenized_words = word_tokenize(text_string)

    # Remove stop words
    if remove_stop_words:
        tokenized_words = [word for word in tokenized_words if word not in stop_words]
    
    tokenized_words_str = " ".join(tokenized_words)
    
    tokenized_words_str = contractions.fix(tokenized_words_str)
    return tokenized_words_str


s = "If y'all are looking for the secret ingredient in Robitussin I believe I have found it. I got this in addition to the Root Beer Extract I ordered (which was good) and made some cherry soda."
clean_text(s,True)

data_df["Text"] = data_df["Text"].apply(lambda x: clean_text(x))
data_df["Summary"] = data_df["Summary"].apply(lambda x: clean_text(x))

data_df["Text_len"] = data_df["Text"].apply(lambda x: len(x.split(" ")))
data_df["Text_len"].hist(bins=30)

max_text_len = 400

data_df["Summary_len"] = data_df["Summary"].apply(lambda x: len(x.split(" ")))
data_df["Summary_len"].hist(bins=30)
max_summary_len = 15

"""From the above Histograms, we have chosen maxlen for Text as 200 and Summary as 10"""

print(data_df.shape)
data_df = data_df[(data_df["Summary_len"] <= max_summary_len) & (data_df["Text_len"] <= max_text_len)]
data_df.shape

data_df['Summary'] = data_df['Summary'].apply(lambda x : 'sostok '+ x + ' eostok')



xTrain,xValid,yTrain,yValid=train_test_split(np.array(data_df['Text']),np.array(data_df['Summary']),test_size=0.2,random_state=0,shuffle=True)

"""tokenising and converting words in sentence as integer sequences
say the sentence 'hello world' is converted to [[0,1],[1,0]] given there are in total 2 distinct words in the entire corpus.
"""

def getNumVocabWordsToBeKept(minReqFreqencyOfWords,tokenizer):

    numRareWords=0
    totalUniqueWords=0
    totalFreqWords = 0
    totalFreqOfRareWords = 0

    for word,freq in tokenizer.word_counts.items():
        totalUniqueWords += 1
        totalFreqWords += freq
        if(freq<minReqFreqencyOfWords):
            numRareWords += 1
            totalFreqOfRareWords+=freq

    print("% of rare words in vocabulary:",(numRareWords/totalUniqueWords)*100)
    print("Total Coverage of rare words:",(totalFreqOfRareWords/totalFreqWords)*100)

    return totalUniqueWords - numRareWords

## getting frequency for X
x_tokenizer = Tokenizer() 
x_tokenizer.fit_on_texts(list(xTrain))

numReqXWords = getNumVocabWordsToBeKept(4,x_tokenizer)

#prepare a tokenizer for reviews on training data
x_tokenizer = Tokenizer(num_words=numReqXWords) 
x_tokenizer.fit_on_texts(list(xTrain))

#convert text sequences into integer sequences
xTrain_seq    =   x_tokenizer.texts_to_sequences(xTrain) 
xValid_seq   =   x_tokenizer.texts_to_sequences(xValid)

#padding zero upto maximum length
xTrain    =   pad_sequences(xTrain_seq,  maxlen=max_text_len, padding='post')
xValid   =   pad_sequences(xValid_seq, maxlen=max_text_len, padding='post')

#size of vocabulary ( +1 for padding token)
xVocab   =  x_tokenizer.num_words + 1

## getting frequency for Y
y_tokenizer = Tokenizer()   
y_tokenizer.fit_on_texts(list(yTrain))
numReqYWords = getNumVocabWordsToBeKept(2,y_tokenizer)

#prepare a tokenizer for reviews on training data
y_tokenizer = Tokenizer(num_words=numReqYWords) 
y_tokenizer.fit_on_texts(list(yTrain))

#convert text sequences into integer sequences
yTrain_seq    =   y_tokenizer.texts_to_sequences(yTrain) 
yValid_seq   =   y_tokenizer.texts_to_sequences(yValid) 

#padding zero upto maximum length
yTrain    =   pad_sequences(yTrain_seq, maxlen=max_summary_len, padding='post')
yValid   =   pad_sequences(yValid_seq, maxlen=max_summary_len, padding='post')

#size of vocabulary
yVocab  =   y_tokenizer.num_words +1

"""##### deleting the rows that contain only START and END tokens"""

def removeRowsWithOnlyStartEnd(textSet,summarySet):
    """
    startEnd tokens are only in summarySet
    """
    ind=[]
    for i in range(len(summarySet)):
        cnt=0
        for j in summarySet[i]:
            if j!=0:
                cnt=cnt+1
        if(cnt==2):
            ind.append(i)

    summarySet=np.delete(summarySet,ind, axis=0)
    textSet=np.delete(textSet,ind, axis=0)
    return textSet,summarySet

xTrain,yTrain = removeRowsWithOnlyStartEnd(xTrain,yTrain)
xValid,yValid = removeRowsWithOnlyStartEnd(xValid,yValid)

len(y_tokenizer.index_word)

len(x_tokenizer.index_word)

tf.keras.backend.clear_session()

latent_dim = 300
embedding_dim=100

########################### Encoder  #####################################
encoder_inputs = Input(shape=(max_text_len,))

#embedding layer
enc_emb =  Embedding(xVocab, embedding_dim,trainable=True,name = 'Input_text_Embedding')(encoder_inputs)

#encoder lstm 1
encoder_lstm1 = LSTM(latent_dim,return_sequences=True,return_state=True,dropout=0.4,recurrent_dropout=0.4,name= "encoder_lstm")
encoder_outputs, state_h, state_c = encoder_lstm1(enc_emb)


################################ decoder #############
# Set up the decoder, using `encoder_states` as initial state.
decoder_inputs = Input(shape=(None,)) ## target vector except the last token

#embedding layer
dec_emb_layer = Embedding(yVocab, embedding_dim,trainable=True,name = 'Summary_text_embedding')
dec_emb = dec_emb_layer(decoder_inputs)

decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True,dropout=0.4,recurrent_dropout=0.2,name = "decoder_lstm")
decoder_lstm_outputs,decoder_fwd_state, decoder_back_state = decoder_lstm(dec_emb,initial_state=[state_h, state_c])

# Attention layer
attentionLayer = Attention(use_scale=True,name = 'Attention') 
attn_out = attentionLayer([decoder_lstm_outputs, encoder_outputs])


# Concat attention input and decoder LSTM output
decoder_concat_input = Concatenate(axis=-1, name='concat_layer')([decoder_lstm_outputs, attn_out])

#dense layer
decoder_dense =  TimeDistributed(Dense(yVocab, activation='softmax'))
decoder_outputs = decoder_dense(decoder_concat_input)

#Define the model 
FullModel = Model([encoder_inputs, decoder_inputs], decoder_outputs)

FullModel.summary()

FullModel.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy')

es = EarlyStopping(monitor='val_loss', mode='min', verbose=1,patience=2)

FullModelcheckpoint = tf.keras.callbacks.ModelCheckpoint("FullModelWeights_100000_epoch_{epoch:02d}_{val_loss:.2f}.h5", monitor='loss', verbose=1,
    save_best_only=False,save_weights_only = True, mode='auto', period=1)

if isTrain == True:
    history=FullModel.fit([xTrain,yTrain[:,:-1]], 
                      yTrain[:,1:] ,
                      epochs=50,callbacks=[es,FullModelcheckpoint],batch_size=200, 
                      validation_data=([xValid,yValid[:,:-1]], yValid[:,1:]))



FullModel.load_weights("./saved_model_100000_nopretrained embeddings/FullModelWeights_100000_epoch_39_1.40.h5")

reverse_target_word_index=y_tokenizer.index_word
reverse_source_word_index=x_tokenizer.index_word
target_word_index=y_tokenizer.word_index

"""## Inference
Set up the inference for the encoder and decoder:
"""

## after the encoder outputs,
decoder_state_input_h = Input(shape=(latent_dim,)) ## hidden state to be initialised , basically the last output of sequence
decoder_state_input_c = Input(shape=(latent_dim,)) ## cell state
encoder_outputs_for_attention = Input(shape=(max_text_len,latent_dim)) ## all sequences required for attention 

## encoder only model so as to get the encoder outputs
encoder_model_inf = Model(inputs=encoder_inputs,outputs=[encoder_outputs, state_h, state_c])

#encoder_model_inf.save("encoderModel.h5")
#encoder_model_inf = tf.keras.models.load_model("encoderModel.h5")

 ## getting the embedings in the summary
dec_emb_inf = dec_emb
## extract decoder outputs for each word
decoder_lstm_output_inf, state_h_decoder, state_c_decoder = decoder_lstm(dec_emb_inf, initial_state=[decoder_state_input_h, decoder_state_input_c]) 

## send the decoder output (1,latentDim) and encoder outputs (maxTextLen, latentDim) into attention layer to get final decoder output
attn_out_inf = attentionLayer([decoder_lstm_output_inf,encoder_outputs_for_attention])

decoder_inf_concat = Concatenate(axis=-1, name='concat')([decoder_lstm_output_inf, attn_out_inf])
decoder_outputs_inf = decoder_dense(decoder_inf_concat) ## time distributed




# Final decoder model for inference
## decoder_inputs : target vector without last token, in this case a single word
decoder_model_inf = Model(
    [decoder_inputs] + [encoder_outputs_for_attention,decoder_state_input_h, decoder_state_input_c],
    [decoder_outputs_inf] + [state_h_decoder, state_c_decoder])


#decoder_model_inf.save_weights("decoderInferenceModel.h5")
#decoder_model_inf.load_weights("decoderInferenceModel.h5")


#decoder_model_inf = tf.keras.models.load_model("decoderInferenceModel.h5")


def decode_sequence(input_seq):
    # Encode the input as state vectors.
    e_out, e_h, e_c = encoder_model_inf.predict(input_seq)
    
    # Generate empty target sequence of length 1.
    target_seq = np.zeros((1,1))
    
    # Populate the first word of target sequence with the start word.
    target_seq[0, 0] = target_word_index['sostok']

    stop_condition = False
    decoded_sentence = ''
    while not stop_condition:
      
        output_tokens, new_h, new_c = decoder_model_inf.predict([target_seq] + [e_out, e_h, e_c])

        # Sample a token
        sampled_token_index = np.argmax(output_tokens[0, -1, :]) ## need to change this to beam search
        sampled_token = reverse_target_word_index[sampled_token_index]
        
        
        if(sampled_token!='eostok'):
            decoded_sentence += ' '+sampled_token

        # Exit condition: either hit max length or find stop word.
        if (sampled_token == 'eostok'  or len(decoded_sentence.split()) >= (max_summary_len-1)):
            stop_condition = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1,1))
        target_seq[0, 0] = sampled_token_index

        # Update internal states
        e_h, e_c = new_h, new_c

    return decoded_sentence

def seq2summary(input_seq):
    newString=''
    for i in input_seq:
        if((i!=0 and i!=target_word_index['sostok']) and i!=target_word_index['eostok']):
            newString=newString+reverse_target_word_index[i]+' '
    return newString

def seq2text(input_seq):
    newString=''
    for i in input_seq:
        if(i!=0):
            newString=newString+reverse_source_word_index[i]+' '
    return newString

for i in range(0,50):
    print("Review:",seq2text(xValid[i]))
    print("Original summary:",seq2summary(yValid[i]))
    print("Predicted summary:",decode_sequence(xValid[i].reshape(1,max_text_len))) 
    print("\n")

