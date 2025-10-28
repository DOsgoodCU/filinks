This is a repo for FI links serving # filinks

It has a few pieces.
  make_fihtml.py 
    uses media_data.csv, news_data.csv, publications_data.csv 
    to generate: financial_instruments.html
    This is a list based on https://iri.columbia.edu/topics/financial-instruments/
    The *_data.csv files were provided by Jeff Turmelle, and edited slightly to fix errors, have news sources, etc.

    the python script has a "cache" option, which I am using for when the IRI website goes down.  
    It creates a cache directory and when activated makes the html point to the cache
    It needs to be thought through (and perhaps not sit in the repo, but be more of a backup)

  scrape_images.py
    scrapes https://iri.columbia.edu/topics/financial-instruments/
    generates image_data.csv and a directory of cached images called images

  find_duplicates.py
    this searches the 3 csv files for potential duplicates and reports them to stdout
    Some of these are not duplicates, but simply have the same title words
  
I need to:
  -Commit and publish soon
  -clean up duplicates and make sure the right source is used (least IRI as possible)
  -add images to the financial_instruments.html
  -check for broken links
  -make sure everything is cached
  -make a version that can create short lists of stuff for donors/partners
  -figure out where to host
  -Use AI to combine columbia commons with publications, using columbia commons when duplicates
  -Use ai to figure out which are not public domain, strategically use iri server with password. 
  -Ask Lauren about prompts for formatting
  -Plan for updating publications (not duplicate with commons)
  -Add desdr links
  -add repo links like okinsure, insurepeople, evacuate, 
  -add links to capstones

  Broken links Ive found:
  Both of these:
      --- Entry 1 (MEDIA from media_data.csv) ---
      title               : A global index insurance design for agriculture
      external_link       : http://agfax.com/2018/09/04/a-global-index-insurance-design-for-agriculture/
      date                : 2018-09-04
      source              : agfax.com
    
      --- Entry 2 (MEDIA from media_data.csv) ---
      title               : A global index insurance design for agriculture
      external_link       : https://www.engineering.columbia.edu/news/global-index-insurance-design-agriculture
      date                : 2018-08-20
      source              : engineering.columbia.edu

  
      
