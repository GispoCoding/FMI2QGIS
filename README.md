# FMI2QGIS
<img src="FMI2QGIS/resources/icons/icon_hr.png" alt="Logo of FMI2QGIS" width="250"/>



![](https://github.com/GispoCoding/FMI2QGIS/workflows/Tests/badge.svg)
![](https://github.com/GispoCoding/FMI2QGIS/workflows/TestsLTR/badge.svg)
![](https://github.com/GispoCoding/FMI2QGIS/workflows/Release/badge.svg)
![codecov.io](https://codecov.io/github/GispoCoding/FMI2QGIS/coverage.svg?branch=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Plugin to view and download Finnish Meteorological Institute's open data


This plugin is used to view and download [Finnish Meteorological Institute's](https://en.ilmatieteenlaitos.fi/) (later FMI)
[open data](https://en.ilmatieteenlaitos.fi/open-data).

Visualizations made with this data as a part of the project can be found [here](https://gispocoding.github.io/FMI2QGIS/).

### Development

Refer to [development](docs/development.md) for developing this QGIS3 plugin.



## Installation instructions

The easiest way to install the plugin is to use the plugin repository within QGIS. Open QGIS, and proceed as follows:

1. Launch the QGIS plugin manager (from the menu bar: Plugins > Manage and Install Plugins...).

2. Go to the 'Settings' tab to make sure that you have checked the 'Show also experimental plugins' checkbox (currently the plugin is still in the development stage and flagged as 'experimental'):


<img src="/images/screenshots/enable_exp_plugins.PNG" alt="Enable experimental plugins" width="600" />

<!-- ![Enable experimental plugins](/images/screenshots/enable_exp_plugins.PNG?raw=true "Enable experimental plugins") -->

3. Go back to 'All' or 'Not installed' tab of the plugin manager and enter the plugin name (FMI2QGIS) to search bar:

4. Choose the plugin and press 'Install Experimental Plugin'.

<img src="/images/screenshots/install_plugin.PNG" alt="Install the plugin" width="600" />

<!-- ![Install the plugin](/images/screenshots/install_plugin.PNG?raw=true "Install the plugin") -->

## Usage

### Adding WFS layers

1. Open the WFS layer dialog from the menu bar > Plugins > FMI2QGIS > Add WFS layers

2. Select the folder where the data is downloaded (if none is selected, the download folder will be the default folder of the QGIS installation).
If you want only to download the data and not add it to the map, uncheck the "Add data to canvas" option.

3. Press "Refresh" to fetch the list of stored queries.

4. Find the correct item from the list, choose it, and press the "Select" button.
   - The parameters available for the chosen item will now open under the bounding box parameters.
   - Choose correct parameters and click "load". Depending on the data and chosen parameters, this may take some time.
   - Also note, that you have to choose the correct parameters according to the stored query (for example, whether the data
     is observational or forecast). Also, the reasonable bounding boxes will depend on the query. See example cases further
     below. Note: if the parameters are not correctly chosen, the server will likely return "the request failed with status
     code 400".

![Selecting and loading WFS layers](/images/screenshots/select_and_load.gif?raw=true "Selecting and loading WFS layers")

- If the data is not showing on the map (and the "add to canvas" checkbox was checked!), make sure the Temporal
Controller is enabled and its time range matches the layer's temporal extent:

![Using the Temporal Controller](/images/screenshots/show_temporal_animation.gif?raw=true "Using the Temporal Controller")


### Adding WMS layers

1. Open the WMS layer dialog from the menu bar > Plugins > FMI2QGIS > Add WMS layers

2. Press "Refresh" to fetch the list of stored queries.

4. Find the correct item from the list, choose it, and press the "Select" button. The parameters available for the chosen
item will be opened under the stored query list. Choose correct parameters and press "Add data to map" button.

![Load WMS layers](/images/screenshots/load_wms_layers.gif?raw=true "Load WMS layers")

### Examples

##### ENFUSER data

The [ENFUSER](https://en.ilmatieteenlaitos.fi/environmental-information-fusion-service) [stored WFS query](http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=GetFeature&storedquery_id=fmi::forecast::enfuser::airquality::helsinki-metropolitan::grid) contains near real-time and forecast data related to air quality in the Helsinki metropolitan
region with a resolution of 20m for the hourly concentrations of PM2.5, PM10, NO2, O3 and Air Quality Index. New dataset
will come available once in an hour. Source: https://www.opendata.fi/data/en_GB/dataset/fmi-enfuser-ilmanlaatumalli

This data can be found as the 4th item on the list from the top. Once selected (following the instructions above), the maximum
temporal extent is automatically updated to the parameter list. The data is from the region contained in the bounding box
defined by the coordinate points (24.58, 60.1321), (24.58, 60.368), (25.1998, 60.368) and (25.1998, 60.1321) in EPSG:4326).

Including all the different concentration types (PM2.5, PM10, NO2, O3 and AQI) for a 24 hour period on the whole region
will result in a downloaded NetCDF file of about 2.5 GB. To reduce the size and time of the download, it is useful to reduce
the temporal and spatial extent of the download as much as possible, or to download only some of the concentrations.

Some visualizations made with the data can be found [here](https://gispocoding.github.io/FMI2QGIS/).

- More examples coming.


## Financial Support

This software has been developed initially as a part of UIA-HOPE innovation competition organized by <a href="https://forumvirium.fi/en/">Forum Virium</a> and that has been financially supported by the European Union's <a href="https://www.uia-initiative.eu/en">Urban Innovative Actions</a> (UIA) Initiative and its <a href="https://www.uia-initiative.eu/en/uia-cities/helsinki">Healthy Outdoor Premises for Everyone</a> project (HOPE).


## License
This plugin is licenced with
[GNU Genereal Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.html).
See [LICENSE](LICENSE) for more information.

This plugins uses [Finnish Meteorological Institute's](https://en.ilmatieteenlaitos.fi/) [open data](https://en.ilmatieteenlaitos.fi/open-data).
By downloading and using the FMI open data, you approve to the Finnish Meteorological Institute's open data
[license](https://en.ilmatieteenlaitos.fi/open-data-licence) (CC BY 4.0):
