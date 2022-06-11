# CropWatch

CropWatch is a project application written in python and built to deliver interactive maps to farmers, showing details of their crops over time.  The data for the maps are time-series data obtained from satellites and other spatiotemporal sources. The application gathers the data from the farms and paddocks via information retrieved from the satellite and other spatiotemporal sources, it then runs cloud-functions on the google cloud platform to export important bands of data. This data is then stored in the a BigQuery database, where the data is further processed and separated into different subsets which are used to create data visualisation reports in DataStudio, that contain maps, graphs and charts that provide transformations and calculations upon the data to provide useful information and insights to farmers, that span back from the current day up to 3 years prior to the current date. 

To utilise CropWatch, as a reference the following things are needed:

-  a PrivateKey (this was not included int he repository but is required for the codes functions to work).
- Access to an AMI project

- earthengine-api (EE) (Google) Earth Engine API 

- google-cloud-storage

- A geojson file with farms/ paddocks details and boundaries data.

- Access to Google Cloud services (Googlee cloud functions, BigQuery, Pubsub, DataStudio).

- Link to the project (https://console.cloud.google.com/welcome?project=aarsc-2022-compsciprac)

- Link to the open source version GitHub repository: https://github.com/Jase-The-Ace/CropWatch

- Please refer to the user manual for detailed usage information.