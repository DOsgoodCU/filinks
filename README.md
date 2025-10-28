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

Only needed to migrate out of old IRI page:
  scrape_images.py
    scrapes https://iri.columbia.edu/topics/financial-instruments/
    generates image_data.csv and a directory of cached images called images
    Should only need to be run the first time Im pulling from the IRI website
 images2news_data.py
   This takes the images scraped above, and adds them to a imagename column in the news_data.csv file.
 
Now make_fihtml.py code is updated to use imagename column in the news_data.csv to look for images
   The way to add an image will be to put it in the images folder, and point to it in the news_data.csv file

  find_duplicates.py
    this searches the 3 csv files for potential duplicates and reports them to stdout
    Some of these are not duplicates, but simply have the same title words
  
I need to:
  -add links to capstones
  -add wiiet links (make sure cached, probalby point to that, include spreadsheet)
  -check for broken links, decide what to do
  -make sure everything is cached, if only backups
  -make a version that can create short lists of stuff for donors/partners
  -figure out where to host
  -Use AI to combine columbia commons with publications, using columbia commons when duplicates
  -Use ai to figure out which are not public domain, strategically use iri server with password. 
  -formatting?
  -Plan for updating publications (not duplicate with commons)


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

  
      
