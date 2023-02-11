.. _languageDocumentation:

Language Selector Documentation
===============================================

Overview
---------------------------------------------

The platform chooses text to be displayed using a simple translation script 
placed in ``Client/src/assets/translation.js`` file. The file contain a simple lookup dictionary, where the keys are descriptors 
for each type of message to be displayed. And the value is another dictionary that lookup actual text based on language code 
as key. 

.. danger:: 

  The actual translated text may not be accurate at the moment, 
  we welcome everyone contributing to improve language option on this page. 

Method 
----------------------------------------------

.. js:autofunction:: dictionaryLookup