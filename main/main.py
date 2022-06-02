import ee
from datetime import date, timedelta, datetime
import time
from google.cloud import storage
from google.oauth2 import service_account
import json

"""
Copyright 2022 Jason O. Aboh, Steve Daniel, Zoe Dowsett, Qiaoling (Ling) Chen
Copyright 2022 James Brinkhoff 

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

# Function to calculate NDVI and other vegetation indicies for each image in a Sentinel-2 collection


def calculate_vegetation_indices(image):
    # B2 = BLUE
    # B3 = GREEN
    # B4 = RED
    # B5 = Visible and Near Infrared
    # B8 = Near Infrared
    # B11 = Short Wave Infrared
    image = ee.Image(image.divide(10000).copyProperties(
        image).copyProperties(image, ['system:time_start']))
    image = image.addBands(
        image.normalizedDifference(['nir', 'r']).rename('ndvi'))
    image = image.addBands(image.normalizedDifference(
        ['nir', 'g']).rename('gndvi'))
    image = image.addBands(
        image.normalizedDifference(['g', 'r']).rename('grvi'))
    image = image.addBands(image.select('nir').divide(
        image.select('g')).subtract(1).rename('cig'))
    image = image.addBands(image.expression(
        '2.5 * ((nir-r) / (nir + 6*r - 7.5*b + 1))', {
            'nir': image.select('nir'),
            'r': image.select('r'),
            'b': image.select('b')
        }).rename('evi'))
    image = image.addBands(image.select(
        'nir').gt(0).unmask(0).rename('unmasked'))
    image = image.addBands(image.normalizedDifference(
        ['g', 'swir1']).rename('mndwi'))
    image = image.addBands(image.normalizedDifference(
        ['nir', 'swir1']).rename('lswi'))
    image = image.addBands(image.select('nir').divide(
        image.select('re')).subtract(1).rename('cire'))
    return image


# Function to mask clouds using the Sentinel-2 QA band.
def maskS2clouds(image):
  # The QA60 bitmask band contains information on the cloud cover for each pixel.
  # So select this band
    qa = image.select('QA60')

  # Bits 10 and 11 are clouds and cirrus, respectively.
  # Use zero fill left shift operators
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11

  # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudBitMask).eq(
        0) and qa.bitwiseAnd(cirrusBitMask).eq(0)

  # Return the masked and scaled data, without the QA bands.
  # The value returned is either null if clouds are obscuring the
  # pixel or the actual value if not
    # return image.updateMask(mask).divide(10000).select("B.*").copyProperties(image, ["system:time_start"])
    return image.updateMask(mask)


def mask_clouds(img):
    # masks clouds in Sentinel-2 collections
    img = ee.Image(img)
    clouds = ee.Image(img.get('cloud_mask')).select('probability')
    isNotCloud = clouds.lt(40)
    return img.updateMask(isNotCloud)


# select the relevant bands and rename to more human-readable heading values
def get_sentinel2_image_collection(start_date, end_date, coll='COPERNICUS/S2_HARMONIZED'):
    sentinel2_image_collection = ee.ImageCollection(coll) \
        .filterDate(start_date, end_date) \
        .select(['B2', 'B3', 'B4', 'B5', 'B8', 'B6', 'B7', 'B8A', 'B11', 'B12', 'QA60'], ['b', 'g', 'r', 're', 'nir', 're74', 're78', 're86', 'swir1', 'swir2', 'QA60'])

    sentinel2_cloud_probability = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')\
        .filterDate(start_date, end_date)

    sentinel2_image_collection = ee.Join.saveFirst('cloud_mask').apply(**{
        'primary': sentinel2_image_collection,
        'secondary': sentinel2_cloud_probability,
        'condition': ee.Filter.equals(leftField='system:index', rightField='system:index')
    })
    return ee.ImageCollection(sentinel2_image_collection).map(maskS2clouds).map(calculate_vegetation_indices)


# get time series over a feature collection, general, doesn't filter ic
def get_timeseries_feature_collection(feature_collection, image_collection, json_file, image_props=[], scale=10):
    def get_time_series_single_feature(feature):
        geom = feature.geometry()

        def sample_image(image):
            return feature.set(image.reduceRegion(**{'reducer': ee.Reducer.mean(), 'geometry': geom, 'scale': scale})) \
                .setGeometry(geom.centroid(10)) \
                .set(image.toDictionary(image_props)) \
                .set('area_gee', geom.area(1).divide(10000)) \
                .set('geojson_filename', json_file)
        samples = image_collection.map(sample_image)
        return samples

    # get time series for a single feature
    time_series = feature_collection.map(get_time_series_single_feature)

    # will be a collection of collections, so need to flatten to a collection
    return time_series.flatten()


def add_date_to_image(image):
    tz = 'Australia/Sydney'
    date = ee.Date(image.get('system:time_start'))
    au_formatted_date = date.format(**{'format': 'yyyy-MM-dd', 'timeZone': tz})
    return image.set({
        'date': au_formatted_date,
    })


def main_function(request):
  # initialize earth engine using json key for service account
    service_account = 'google-earth-engine-service-ac@aarsc-2022-compsciprac.iam.gserviceaccount.com'
    privateKey = 'sa-private-key.json'

    # authenticate using service account
    credentials = ee.ServiceAccountCredentials(service_account, privateKey)
    ee.Initialize(credentials)

    # get optional POST argument for the json filename
    request_json = request.get_json(silent=True)
    request_args = request.args
    if request_json and 'json_filename' in request_json:
        json_filename = request_json['json_filename']
    elif request_args and 'json_filename' in request_args:
        json_filename = request_args['json_filename']
    else:
        json_filename = 'farm_details.json'

    # set the start and end dates for the code
    # this should be moved to arguments in the future
    # start with a 3 year timeframe (1095 days)
    start_date = (date.today() - timedelta(days=1095)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    # load a geojson file to get farm details
    # json_filename = 'farm_details.json'
    json_file = open(json_filename)
    feature_collection_json = json.load(json_file)
    json_file.close()

    # create the feature collection based on the geojson supplied
    feature_collection = ee.FeatureCollection(feature_collection_json)

    # extract the farm boundaries from the feature collection
    geom = feature_collection.geometry().bounds()

    # create an image collection from the sentinel2 satellite images using the date ranges and geo boundaries
    # - collection of S2 images covering the feature collection of interest
    sentinel2_image_collection = get_sentinel2_image_collection(
        start_date, end_date).filterBounds(geom).map(add_date_to_image)

    # gets image statistics at each time over each field defined in feature collection
    time_series = get_timeseries_feature_collection(feature_collection, sentinel2_image_collection, json_filename, image_props=[
                                                    'date', 'ndvi', 'gndvi', 'grvi', 'cig', 'mndwi', 'lswi', 'cire'], scale=10)

    # Function to export statistical values per ID with the information of day, month and year
    task = ee.batch.Export.table.toCloudStorage(
        collection=time_series,
        description='farm_data_export_'+str(datetime.now().year) + "-" + str(datetime.now().month) + "-" + str(
            datetime.now().day) + " " + str(datetime.now().hour) + ":" + str(datetime.now().minute),
        outputBucket='aarsc-2022-compsciprac-csv-databucket',
        fileFormat='csv'
        # selectors=['date','id','ndvi','gndvi','grvi','cig','mndwi','lswi','cire']
    )
    task.start()

    return "completed"
