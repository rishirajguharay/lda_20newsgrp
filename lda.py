# -*- coding: utf-8 -*-
"""lda.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oZNNysYrvcjI26GLKDJvH-DxXIMFmB4Y
"""

import re
import string
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.datasets import fetch_20newsgroups

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import gensim
from gensim import corpora
from gensim.models.ldamodel import LdaModel
from gensim.models import CoherenceModel

import spacy
nlp = spacy.load('en')

import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

dataset_train = fetch_20newsgroups(subset='train', remove=('headers', 'footers', 'quotes'), shuffle=True, random_state=42)
df = pd.DataFrame()
df["text"] = dataset_train.data
df["label"] = dataset_train.target
df["lname"] = df["label"].apply(lambda r : dataset_train["target_names"][r] )

def cleaning(text):
  text = re.sub('\S*@\S*\s?', '',text) #remove emails
  #text = re.sub('\s+', ' ', text) #new line #not required, handled during tokenisation
  #text = re.sub("\'", " ", text) #single quotes
  text= re.sub('((www\.[^\s]+)|(https?://[^\s]+))',' ',text) #remove links
  #translator = str.maketrans('','',string.punctuation) #!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
  #text = text.translate(translator) 
  return text;

from gensim.parsing.preprocessing import STOPWORDS

def lemmatization(text):
  word = gensim.utils.simple_preprocess(text, min_len=3,deacc=True) #list of tokens
  sent=[]
  text_p = ' '.join(word)
  doc = nlp(text_p)
  sent.extend([token.lemma_ for token in doc if token.pos_ not in ['PRON']and token.lemma_.islower()])
  sent = [token.strip() for token in sent] #remove extraspace around tokens
  sent = [token for token in sent  if token not in STOPWORDS] #remove stopwords
  return sent

df['processed_text'] =df['text'] 
df['processed_text'] = df['processed_text'].apply(cleaning)
df['processed_text'] = df['processed_text'].str.lower()
#df['processed_text']
df['processed_text'] = df['processed_text'].apply(lemmatization)
df['processed_text']

dictionary = gensim.corpora.Dictionary(df['processed_text'])
dictionary.filter_extremes(no_below=5, no_above=0.1, keep_n=13000)
bow_corpus = [dictionary.doc2bow(doc) for doc in df['processed_text']]
lda_model =  gensim.models.LdaMulticore(bow_corpus, 
                                   num_topics = 20, 
                                   id2word = dictionary,                                    
                                   passes = 10,
                                   workers = 3)

lda_model =  gensim.models.ldamodel.LdaModel(passes=10,corpus=bow_corpus,id2word=dictionary,num_topics = 8)

search_params = {
'decay' : [0.3,0.5,0.7],
'iterations' : [30, 50, 70],
'chunksize' : [1000, 2000, 3000]
}

import itertools
train = []
best_coherence_score = 0.0
best_log_perplexity = 0.0
c=0
for params in itertools.product(*search_params.values()):
  check = []
  check.append(params[0])
  check.append(params[1])
  check.append(params[2])
  lda_model =  gensim.models.ldamodel.LdaModel(corpus=bow_corpus,id2word=dictionary, update_every=1, chunksize=params[2],random_state=100,
                                             alpha='auto', eta='auto', decay= params[0], offset=1.0, eval_every=10, iterations= params[1], gamma_threshold=0.001, minimum_probability=0.01, ns_conf=None, minimum_phi_value=0.01, per_word_topics=False, callbacks=None)
  coherencemodel = CoherenceModel(model=lda_model,texts=df['processed_text'],corpus=bow_corpus,dictionary=dictionary, coherence='c_v')
  coherence_score = coherencemodel.get_coherence()
  check.append(coherence_score)   
  log_perplexity = lda_model.log_perplexity(bow_corpus)
  check.append(log_perplexity)

  if  coherence_score > best_coherence_score:
    best_coherence_score = coherence_score   
    best_lda_model_c = lda_model
    best_params = params   
  if  log_perplexity < best_log_perplexity:
    best_log_perplexity = log_perplexity   
    best_lda_model_p = lda_model
    best_params_preplexity = params   
  train.append(check)

  print(params, coherence_score)
         
param = ['decay','iterations','chunksize', 'coherence score', 'log perplexity']
df_model = pd.DataFrame(train, columns = param)
df_model

coherencemodel = CoherenceModel(model=lda_model,texts=df['processed_text'],corpus=bow_corpus,dictionary=dictionary, coherence='c_v',topn=4)
coherence_score = coherencemodel.get_coherence()
coherence_score

for idx, topic in lda_model.print_topics(-1):
    print("Topic: {} \nWords: {}".format(idx, topic ))
    print("\n")

def per_topic_words(topw):
  topics_keywords = []
  for i in range(lda_model.num_topics):
    word_perlist=[]
    for j in range(topw):
      word_perlist.append(lda_model.show_topic(i,topw)[j][0])
    topics_keywords.append(word_perlist)
  return topics_keywords  
topic_keywords = per_topic_words(10)
df_topic_keywords = pd.DataFrame(topic_keywords)
df_topic_keywords.columns = ['W '+str(i) for i in range(df_topic_keywords.shape[1])]
#df_topic_keywords.index = ['T '+str(i) for i in range(df_topic_keywords.shape[0])]
df_topic_keywords

#Get the topic distribution for the given document, #doc in bow format
df_doc_topic = pd.DataFrame(columns = ['Doc_ID', 'Dominant_Topic', 'Prob_Per_Topic', 'Keywords', 'Doc_Text'])
for i in range(len(bow_corpus)):
  a = lda_model.get_document_topics(bow_corpus[i])
  a.sort(key = lambda x: x[1], reverse=True) #highest prob topic first
  topic_wp = lda_model.show_topic(a[0][0]) #show top 10 words byb default
  keywords = [w for (w,p) in topic_wp]
  row = [i, a[0][0], a[0][1], keywords,  df['processed_text'][i]]
  df_doc_topic.loc[i] = row

df_doc_topic.head(10)

df_doc_topic.iloc[df_doc_topic[df_doc_topic["Dominant_Topic"]==5].index]

lda_model.show_topic(11, topn=20)

topic_counts = df_doc_topic.groupby('Dominant_Topic').agg('count')
topic_counts.reset_index(level=0,inplace=True)
topic_counts = topic_counts[['Dominant_Topic','Keywords']].rename(columns= {'Dominant_Topic':'Topic','Keywords':'Total Docs'})
topic_counts['Keywords']=topic_counts['Topic'].apply(get_keyword)
topic_counts.sort_values('Total Docs',ascending=False)

def get_keyword(topic):
  topic = int(topic)
  wp = lda_model.show_topic(topic)
  topic_keywords = ", ".join([word for word, prop in wp])
  return topic_keywords

