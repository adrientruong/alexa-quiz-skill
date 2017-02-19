import argparse
import subprocess
import timeit
import logging
import math
import numpy as np
import time
import sys
import re
import json
import bing as b
from watson_developer_cloud import AlchemyLanguageV1

alchemy_language = AlchemyLanguageV1(api_key='65c86442fcf992a2dbedd5d4a4bee9937cecc006')
bing = b.BingSpeechAPI()

def generate():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vocab_file', default='vocab.txt', type=str)
    parser.add_argument('--vectors_file', default='vectors.txt', type=str)
    args = parser.parse_args()

    with open(args.vocab_file, 'r') as f:
        words = [x.rstrip().split(' ')[0] for x in f.readlines()]
    with open(args.vocab_file, 'r') as f:
        counts = [int(x.rstrip().split(' ')[1]) for x in f.readlines()]
    with open(args.vectors_file, 'r') as f:
        vectors = {}
        for line in f:
            vals = line.rstrip().split(' ')
            vectors[vals[0]] = [float(x) for x in vals[1:]]

    vocab_size = len(words)
    vocab = {w: idx for idx, w in enumerate(words)}
    ivocab = {idx: w for idx, w in enumerate(words)}

    vector_dim = len(vectors[ivocab[0]])
    W = np.zeros((vocab_size, vector_dim))
    for word, v in vectors.items():
        if word == '<unk>':
            continue
        W[vocab[word], :] = v

    # normalize each word vector to unit variance
    W_norm = np.zeros(W.shape)
    d = (np.sum(W ** 2, 1) ** (0.5))
    x = 0
    # print "LenW: " + str(W.shape)
    # print "LenD: " + str(d.shape)
    W_norm = (W.T / d).T
    return (W_norm, vocab, ivocab, counts)


def distance(W, vocab, ivocab, input_term, universe):
    for idx, term in enumerate(input_term.split(' ')):
        if term in vocab:
            # print('Word: %s  Position in vocabulary: %i' % (term, vocab[term]))
            if idx == 0:
                vec_result = W[vocab[term], :] 
            else:
                vec_result += W[vocab[term], :] 
        else:
            # print('Word: %s  Out of dictionary!\n' % term)
            # vocab[term] = len(vocab)
            return None
    
    vec_norm = np.zeros(vec_result.shape)
    d = (np.sum(vec_result ** 2,) ** (0.5))
    vec_norm = (vec_result.T / d).T

    dist = np.dot(W, vec_norm.T)

    for term in input_term.split(' '):
        index = vocab[term]
        # dist[index] = -np.Inf

    a = np.argsort(-dist)
    return dist

# http://stackoverflow.com/questions/2460177/edit-distance-in-python
def ld(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def getDistance(word1, word2, dist, vocab):
    editDist = ld(word1, word2)
    score = (len(word1) - editDist) / float(len(word1))
    return max(score, getCosineDistance(word1, word2, dist, vocab))

def getCosineDistance(word1, word2, dist, vocab):
    if word1 in vocab and word2 in vocab:
        return dist[vocab[word2]]
    elif word1 == word2:
        return 1.0
    else:
        return 0.0

def getMultiplier(word1, counts, vocab, average):
    if word1 in vocab:
        return 1.0/math.log(counts[vocab[word1]], 2)
    else:
        return 1.0/math.log(average, 2)

def getConceptScore(words1, words2):
    try:
        keywords = alchemy_language.keywords(text=words1)
        if (not keywords or not 'keywords' in keywords or len(keywords['keywords']) <= 1):
            return (0.0, 0.0)
        words = ''
        for keyword in keywords['keywords']:
            words += keyword['text'] + ' '
        print "You said: ", words
        return (getScore(words, words2), 1.0)
    except:
        return (0.0, 0.0)

W, vocab, ivocab, counts = generate()
universe = {}
total = sum(counts)
average = float(total) / len(counts)

def getScore(words1, words2):
    print "words1 now ", words1
    input_sentence_1 = re.sub(" +", ' ', re.sub("[^a-z0-9' ]", ' ', words1.lower())).strip().split(' ')
    input_sentence_2 = re.sub(" +", ' ', re.sub("[^a-z0-9' ]", ' ', words2.lower())).strip().split(' ')
    print "Comparing", input_sentence_1, "|", input_sentence_2
    additions = 0.0
    score = 0.0
    
    # print input_sentence_1, input_sentence_2
    for word in input_sentence_1:
        dist = distance(W, vocab, ivocab, word, universe)
        b = []
        c = []
        for word2 in input_sentence_2:
            b.append((word2, getDistance(word, word2, dist, vocab)))
            c.append(getDistance(word, word2, dist, vocab))
        # print "added " + str(max(c) * getMultiplier(word, counts, vocab, average)), ", weight", getMultiplier(word, counts, vocab, average)
        score += max(c) * getMultiplier(word, counts, vocab, average)
        additions += getMultiplier(word, counts, vocab, average)
        # print word, b
    score /= additions 
    return score


def isCorrect(words1, words2):
    words1 = re.sub("\(.*?\)", "", words1)
    score1 = getScore(words1, words2)
    score2, total = getConceptScore(words1, words2)
    score = (score1 + score2) / (1.0 + total)
    print score1, score2, score
    return score > 0.6

def getMp3(text):
    try:
        stream = None
        logging.basicConfig(level=logging.DEBUG)
        print('TTS:{}'.format(text))
        speech = bing.synthesize(text, stream=stream)
        wav = bing.to_wav(speech)
        open('x.wav', 'w').write(wav)
        wav = 'x.wav'
        cmd = 'ffmpeg -i x.wav -ac 2 -codec:a libmp3lame -b:a 48k -ar 16000 x.mp3'
        #cmd = 'lame --preset insane %s' % wav
        subprocess.call('rm -f x.mp3', shell=True)
        subprocess.call(cmd, shell=True)
        return 'x.mp3'
    except:
        print "fail"
        pass

#getMp3('Estas escuchando una prueba del sistema TTS con la voz de %s como demostracion de la gran utilidad de poder convertir un texto en voz real.')
#getMp3(raw_input())
