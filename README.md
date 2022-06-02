# CropWatch

CropWatch is a project application written in python and built to deliver interactive maps to farmers, showing details of their crops over time.  The data for the maps are time-series data obtained from satellites and other spatio-temporal sources. The application gathers the data from the farms and paddocks via information retreived from the satelite and other spatio temporal sources, it then runs cloud-functions on the google cloud platform to export important bands of data. This data is then stored in the a BigQuery database, where the data is further processed and seperated into different subsets which are used to create data studio reports that contain maps, graphs and charts that provide transformations and calculations upon the data to provide useful information and insights to farmer, that span back from the currrent day about 3 years prior. 

To utilise CropWatch, as a reference the following things are needed:

-  a PrivateKey (this was not included int he repository but is required for the codes functions to work).
- Access to an AMI project
- earthengine-api (EE) (Google) Earth Engine API 
- google-cloud-storage