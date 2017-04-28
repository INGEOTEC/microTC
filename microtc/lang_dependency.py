# Copyright 2016 Sabino Miranda-Jiménez and Daniela Moctezuma
# with collaborations of Eric S. Tellez

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-

import io
import re
import os
import logging
from nltk.stem.snowball import SnowballStemmer
from .params import OPTION_GROUP, OPTION_DELETE, OPTION_NONE
from nltk.stem.porter import PorterStemmer
from nltk.stem.isri import ISRIStemmer
from stop_words import get_stop_words as arabic_get_stop_words
import nltk

idModule = "language_dependency"
logger = logging.getLogger(idModule)
ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# formatterC = logging.Formatter('%(asctime)s\t%(levelname)s\t%(filename)s\t%(message)s')
formatterC = logging.Formatter('%(module)s-%(funcName)s\n\t%(levelname)s\t%(message)s')
ch.setFormatter(formatterC)
logger.addHandler(ch)

PATH = os.path.join(os.path.dirname(__file__), 'resources')

_HASHTAG = '#'
_USERTAG = '@'
_sURL_TAG = '_url'
_sUSER_TAG = '_usr'
_sHASH_TAG = '_htag'
_sNUM_TAG = '_num'
_sDATE_TAG = '_date'
_sENTITY_TAG = '_ent'
_sNEGATIVE = "_neg"
_sPOSITIVE = "_pos"
_sNEUTRAL = "_neu"

_ARABIC ="arabic"
_ENGLISH = "english"
_SPANISH = "spanish"
_ITALIAN = "italian"
_GERMAN = "german"

_ar_ARABIC = "ar"

class LangDependencyError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class LangDependency():
    """
    Defines a set of functions to change text using laguage dependent transformations, e.g., 
    - Negation
    - Stemming
    - Stopwords
    """
    STOPWORDS_CACHE = {}
    NEG_STOPWORDS_CACHE = {}

    def __init__(self, lang=_SPANISH):
        """
        Initializes the parameters for specific language
        """
        self.languages = [_SPANISH, _ENGLISH, _ITALIAN, _GERMAN, _ARABIC]
        self.lang = lang

        if self.lang not in self.languages:
            raise LangDependencyError("Language not supported: " + lang)
        
        self.stopwords = LangDependency.STOPWORDS_CACHE.get(lang, None)
        if self.stopwords is None:
            if self.lang == _ARABIC:
                self.stopwords = arabic_get_stop_words(_ar_ARABIC)
            else:
                self.stopwords = self.load_stopwords(os.path.join(PATH, "{0}.stopwords".format(lang)))
            LangDependency.STOPWORDS_CACHE[lang] = self.stopwords

        self.neg_stopwords = LangDependency.NEG_STOPWORDS_CACHE.get(lang, None)
        if self.neg_stopwords is None:
            self.neg_stopwords = self.load_stopwords(os.path.join(PATH, "{0}.neg.stopwords".format(lang)))
            LangDependency.NEG_STOPWORDS_CACHE[lang] = self.neg_stopwords

        if self.lang not in SnowballStemmer.languages and self.lang != _ARABIC:
                raise LangDependencyError("Language not supported for stemming: " + lang)

        if self.lang == _ENGLISH:
            self.stemmer = PorterStemmer()
        elif self.lang == _ARABIC:
            self.stemmer = ISRIStemmer()
        else:
            self.stemmer = SnowballStemmer(self.lang)

    def load_stopwords(self, fileName):
        """
        it loads stopwords from file
        """
        logger.debug("loading stopwords... " + fileName)
        if not os.path.isfile(fileName):
            raise LangDependencyError("File not found: " + fileName)
        
        StopWords = []
        with io.open(fileName, encoding='utf8') as f:
            for line in f.readlines():
                line = line.strip().lower()
                if line == "":
                    continue
                if line.startswith("#"):
                    continue
                StopWords.append(line)

        M = "|".join(StopWords)
        return re.compile(r"\b(" + M + r")\b", flags=re.I)

    def stemming(self, text):
        """
        Applies the stemming process to `text` parameter
        """
        
        tokens = re.split(r"~", text.strip())
        t = []
        for tok in tokens:
            if re.search(r"^(@|#|_|~)", tok, flags=re.I):
                t.append(tok)
            else:
                try:
                    t.append(self.stemmer.stem(tok))
                except IndexError:
                    t.append(tok)

        return "~".join(t)

    def negation(self, text):
        """
        Applies negation process to the given text
        """
        if self.lang not in self.languages:
            raise LangDependencyError("Negation - language not defined")
        
        
        if self.lang == _SPANISH:
            text = self.spanish_negation(text)
        elif self.lang == _ENGLISH:
            text = self.english_negation(text)
        elif self.lang == _ITALIAN:
            text = self.italian_negation(text)
        elif self.lang == _ARABIC:
            #not supported yet
            pass
        return text

    def spanish_negation(self, text):
        """
        Standarizes negation sentences, nouns are also considering with the operator "sin" (without)
        Markers like ninguno, ningún, nadie are considered as another word.
        """
        if getattr(self, 'skip_words', None) is None:
            self.skip_words = "me|te|se|lo|les|le|los"
            self.skip_words = self.skip_words + "|" + "|".join(self.neg_stopwords)

        text = text.replace('~', ' ')
        tags = _sURL_TAG + "|" + _sUSER_TAG + "|" + _sENTITY_TAG + "|" + \
               _sHASH_TAG + "|" + \
               _sNUM_TAG + "|" + _sNEGATIVE + "|" + \
               _sPOSITIVE + "|" + _sNEUTRAL + "|"
        
        # unifies negation markers under the "no" marker 
        text = re.sub(r"\b(jam[aá]s|nunca|sin|ni|nada)\b", " no ", text, flags=re.I)
        # reduces to unique negation marker        
        text = re.sub(r"\b(jam[aá]s|nunca|sin|no|nada)(\s+\1)+", r"\1", text, flags=re.I)
        p1 = re.compile(r"(?P<neg>((\s+|\b|^)no))(?P<sk_words>(\s+(" +
                        self.skip_words + "|" + tags + r"))*)\s+(?P<text>(?!(" +
                        tags + ")(\s+|\b|$)))", flags=re.I)
        m = p1.search(text)
        if m:
            text = p1.sub(r"\g<sk_words> \g<neg>_\g<text>", text)
        # removes isolated marks "no_" if marks appear because of negation rules
        text = re.sub(r"\b(no_)\b", r" no ", text, flags=re.I)
        # removes extra spaces because of transformations 
        text = re.sub(r"\s+", r" ", text, flags=re.I)
        return text.replace(' ', '~')

    def english_negation(self, text):
        """
        Standarizes negation sentences
        markers used:
                     "not, no, never, nor, neither"
                     "any" is only used with negative sentences.  
        """
        
        if getattr(self, 'skip_words', None) is None:
            self.skip_words = "me|you|he|she|it|us|the"
            self.skip_words = self.skip_words + "|" + "|".join(self.neg_stopwords)
            
        text = text.replace('~', ' ')
        tags = _sURL_TAG + "|" + _sUSER_TAG + "|" + _sENTITY_TAG + "|" + \
            _sHASH_TAG + "|" + \
            _sNUM_TAG + "|" + _sNEGATIVE + "|" + \
            _sPOSITIVE + "|" + _sNEUTRAL + "|"
  
        # expands contractions of negation
        text = re.sub(r"\b(ca)n't\b", r"\1n not ", text, flags=re.I)
        text = re.sub(r"\b(w)on't\b", r"\1ill not ", text, flags=re.I)
        text = re.sub(r"\b(sha)n't\b", r"\1ll not ", text, flags=re.I)
        text = re.sub(r"\b(can)not\b", r"\1 not ", text, flags=re.I)
        text = re.sub(r"\b([a-z]+)(n't)\b", r"\1 not ", text, flags=re.I)

        # checks negative sentences with the "any" marker and changes "any" to "not" makers
        pp1 = re.compile(r"(?P<neg>(\bnot\b))(?P<text>(\s+([^\s]+?)\s+)+?)(?P<any>any\b)", flags=re.I)
        m = pp1.search(text)
        if m:
            text = pp1.sub(r"\g<neg> \g<text> not ", text)
            
        # unifies negation markers under the "not" marker
        # markers used:
        #              not, no, never, nor, neither
        text = re.sub(r"\b(not|no|never|nor|neither)\b", r" not ", text, flags=re.I)
        text = re.sub(r"\s+", r" ", text, flags=re.I)

        p1 = re.compile(r"(?P<neg>((\s+|\b|^)not))(?P<sk_words>(\s+(" + \
                        self.skip_words + "|" + tags + r"))*)\s+(?P<text>(?!(" + \
                        tags + ")(\s+|\b|$)))", flags=re.I)
        m = p1.search(text)
        if m:
            text = p1.sub(r"\g<sk_words> \g<neg>_\g<text>", text)
        # removes isolated marks "no_" if marks appear because of negation rules
        text = re.sub(r"\b(not_)\b", r" not ", text, flags=re.I)
        text = re.sub(r"\s+", r"~", text, flags=re.I)
        return text

    def italian_negation(self, text):
        if getattr(self, 'skip_words', None) is None:
            self.skip_words = "mi|ti|lo|gli|le|ne|li|glieli|glielo|gliela|gliene|gliele"
            self.skip_words = self.skip_words + "|" + "|".join(self.neg_stopwords)
       
        text = text.replace('~', ' ')
        tags = _sURL_TAG + "|" + _sUSER_TAG + "|" + _sENTITY_TAG + "|" + \
               _sHASH_TAG + "|" + \
               _sNUM_TAG + "|" + _sNEGATIVE + "|" + \
               _sPOSITIVE + "|" + _sNEUTRAL + "|"
		
 
        # unifies negation markers under the "no" marker                
        text = re.sub(r"\b(mai|senza|non|no|né|ne)\b", " no ", text, flags=re.I)
		
        # reduces to unique negation marker   		
        text = re.sub(r"\b(mai|senza|non|no|né|ne)(\s+\1)+", r"\1", text, flags=re.I)
		
        p1 = re.compile(r"(?P<neg>((\s+|\b|^)no))(?P<sk_words>(\s+(" +
                        self.skip_words + "|" + tags + r"))*)\s+(?P<text>(?!(" +
                        tags + ")(\s+|\b|$)))", flags=re.I)
        
        m = p1.search(text)	
        
        if m:
            text = p1.sub(r"\g<sk_words> \g<neg>_\g<text>", text)

        # removes isolated marks "no_" if marks appear because of negation rules
        text = re.sub(r"\b(no_)\b", r" no ", text, flags=re.I)
        # removes extra spaces because of transformations 
        text = re.sub(r"\s+", r" ", text, flags=re.I)
        return text.replace(' ', '~')
    
    def filterStopWords(self, text, stopwords_option):
        if stopwords_option != OPTION_NONE:
            # for sw in self.stopwords:
            if stopwords_option == OPTION_DELETE:
                # text = re.sub(r"\b(" + sw + r")\b", r"~", text, flags=re.I)
                text = self.stopwords(r"~", text, flags=re.I)
            elif stopwords_option == OPTION_GROUP:
                # text = re.sub(r"\b(" + sw + r")\b", r"~_sw~", text, flags=re.I)
                text = self.stopwords(r"~_sw~", text, flags=re.I)

        return text
    
    def transform(self, text, negation=False, stemming=False, stopwords=OPTION_NONE):
        if negation:
            text = self.negation(text)

        if stemming:
            text = self.stemming(text)

        text = self.filterStopWords(text, stopwords)
        return text

    def extract_entity_names(self, t):
        entity_names = []
        if hasattr(t, 'label') and t.label:
            if t.label() == 'NE':
                entity_names.append(' '.join([child[0] for child in t]))
            else:
                for child in t:
                    entity_names.extend(self.extract_entity_names(child))

        return entity_names

    def identify_entities(self, text):
        sentences = nltk.sent_tokenize(text)
        tokenized_sentences = [nltk.word_tokenize(sentence) for sentence in sentences]
        tagged_sentences = [nltk.pos_tag(sentence) for sentence in tokenized_sentences]
        chunked_sentences = nltk.ne_chunk_sents(tagged_sentences, binary=True)
        entity_names = []
        for tree in chunked_sentences:
            entities = self.extract_entity_names(tree)
            entity_names.extend(entities)
        return entity_names
        
    def process_entities(self, text, option=OPTION_GROUP):
        """
        Groups or deletes the entities identified in 'text' 
        """
        # Today, NE Recognition is only supported for English
        if self.lang != _ENGLISH:
            return text
        
        if option == OPTION_GROUP or option == OPTION_DELETE:
            entity_names = self.identify_entities(text)
            entity = _sENTITY_TAG 
            for ent in entity_names:
                if option == OPTION_DELETE:
                    entity = ""

                text = re.sub(r"\b(" + ent + r")\b", entity, text, flags=re.I)

        return text


