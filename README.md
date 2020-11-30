# FMI2QGIS
<img src="FMI2QGIS/resources/icons/icon_hr.png" alt="Logo of FMI2QGIS" width="250"/>



![](https://github.com/GispoCoding/FMI2QGIS/workflows/Tests/badge.svg)
![](https://github.com/GispoCoding/FMI2QGIS/workflows/Release/badge.svg)


Plugin to view and download Finnish Meteorological Institute's open data


This plugin is used to view and download [Finnish Meteorological Institute's](https://en.ilmatieteenlaitos.fi/) (later FMI)
[open data](https://en.ilmatieteenlaitos.fi/open-data).

### Development

Refer to [development](docs/development.md) for developing this QGIS3 plugin.



## Installation instructions

The easiest way to install the plugin is to use the plugin repository within QGIS. So open QGIS, and proceed as follows:

1. Launch the QGIS plugin manager (from the menu bar: Plugins > Manage and Install Plugins...).

2. Go to the 'Settings' tab to make sure that you have checked the 'Show also experimental plugins' checkbox (currently the plugin is still in the development stage and flagged as 'experimental'):

![Enable experimental plugins](/images/screenshots/enable_exp_plugins.gif?raw=true "Enable experimental plugins")

3. Go back to 'All' or 'Not installed' tab of the plugin manager and enter the plugin name (FMI2QGIS) to search bar:

4. Choose the plugin and press 'Install Experimental Plugin'.

![Install the plugin](/images/screenshots/install_plugin.gif?raw=true "Install the plugin")
 


## Usage

### Adding WFS layers

1. Open the WFS layer dialog from the menu bar > Plugins > FMI2QGIS > Add WFS layers

2. Select the folder where the data is downloaded (if none is selected, the download folder will be the default folder of the QGIS installation).
If you want only to download the data and not add it to the map, uncheck the "Add data to canvas" option.

3. Press "Refresh" to fetch the list of stored queries. 

4. Find the correct item from the list, choose it, and press the "Select" button. The parameters available for the chosen
item will be opened under the bounding box parameters. Choose correct parameters and click "load". Depending on the data
and chosen parameters, this may take some time. Also note, that you have to choose the correct parameters according to the 
stored query (for example, whether the data is observational or forecast). Also, the reasonable bounding boxes will depend 
on the query. See example cases further below.

![Selecting and loading WFS layers](/images/screenshots/select_and_load.gif?raw=true "Selecting and loading WFS layers")

### Adding WMS layers


## Financial Support

This software has been developed initially as a part of UIA-HOPE innovation competition organized by <a href="https://forumvirium.fi/en/">Forum Virium</a> and that has been financially supported by the European Union's <a href="https://www.uia-initiative.eu/en">Urban Innovative Actions</a> (UIA) Initiative and its <a href="https://www.uia-initiative.eu/en/uia-cities/helsinki">Healthy Outdoor Premises for Everyone</a> project (HOPE).


## License
This plugin is licenced with 
[GNU Genereal Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.html). 
See [LICENSE](LICENSE) for more information.

This plugins uses [Finnish Meteorological Institute's](https://en.ilmatieteenlaitos.fi/) [open data](https://en.ilmatieteenlaitos.fi/open-data).
By downloading and using the FMI open data, you approve to the Finnish Meteorological Institute's open data 
[license](https://en.ilmatieteenlaitos.fi/open-data-licence) (CC BY 4.0): 
