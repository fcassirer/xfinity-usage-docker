**Xfinity (Comcast) Data Usage Scrapper in Docker**
------------------------------

This is a combination of two repos:
```
https://github.com/jantman/xfinity-usage
https://github.com/billimek/comcastUsage-for-influxdb
```

This includes a modified xfinity-usage python module. Refer to the following:
https://github.com/jantman/xfinity-usage/issues/30
https://github.com/billimek/comcastUsage-for-influxdb/issues/1

xfinity-usage was modified to resolve the above state issues and control request attempt looping.

Status:
As of today (2021.01.31), this container is working accurately to scrap xfinity account data. I only perform the data request action 2 times per day, since I presume (based on other user's reports) that xFinity will block your username if you request too often. Use at your own discretion !!!!



![Screenshot](images/comcast_grafana_example.png)

This tool allows you to run periodic data usage checks and save the results to file and/or Influxdb




This code is adopted from the work done by [barrycarey](https://github.com/barrycarey) in the [similar thing for capturing speedtest data](https://github.com/barrycarey/Speedtest-for-InfluxDB-and-Grafana) as well as [jantman's](https://github.com/jantman) [xfinity-usage python example](https://github.com/jantman/xfinity-usage)

## Configuration within config.ini

#### GENERAL
|Key            |Description                                                                                                         |
|:--------------|:-------------------------------------------------------------------------------------------------------------------|
|Interval       |Interval is seconds between each scraping scheduled task                                                            |
|Iterations     |Iterations is the count of scrap tasks performed before exit; set to zero for indefinite                            |
|Attempts       |Attempts is the number of web requests errors before failure                                                        |
|Verbose        |Verbose produces debug log and screenprints to '/data'                                                              |
#### XFINITY
|Key            |Description                                                                                                         |
|:--------------|:-------------------------------------------------------------------------------------------------------------------|
|Username       |Comcast username (don't include the @comcast.com)                                                                   |
|Password       |Password for above user  
#### LOG
|Key            |Description                                                                                                         |
|:--------------|:-------------------------------------------------------------------------------------------------------------------|
|Enabled        |Set to True to activate 
#### FILE
|Key            |Description                                                                                                         |
|:--------------|:-------------------------------------------------------------------------------------------------------------------|
|Enabled        |Set to True to activate  
|Filename       |JSON output is written to to '/data'. default = output.json                                                         |
#### INFLUXDB
|Key            |Description                                                                                                         |
|:--------------|:-------------------------------------------------------------------------------------------------------------------|
|Address        |Delay between updating metrics                                                                                      |
|Port           |InfluxDB port to connect to.  8086 in most cases                                                                    |
|Database       |Database to write collected stats to                                                                                |
|Username       |User that has access to the database                                                                                |
|Password       |Password for above user                                                                                             |



## InfluxDB metrics
```
'measurement': 'comcast_data_usage',
'fields': {
		'used',
		'total',
		'unit'
}
```

## Grafana singlestat example
See this [example json](example.json) for a singlestat panel as shown in the screenshot above

## Usage



#### Requirements

Docker
Currently running on Debian Linux x86, will likely continue further testing on Raspbian for arm32/64 arch

## Docker Setup

1. Install [Docker](https://www.docker.com/)

2. Clone repo in local folder

3. Alter config.ini as desired
Example:
```
[XFINITY]
Username = annoying_customer
Password = supersecretpassword
```

4. Run the container, pointing to the directory with the config file, and an output folder (optional,recommended).
```bash
docker run \
   --name="xfinity" \
   -v /some/path/config.ini:/app/config.ini \
   -v /some/path/data:/app/data \
   xfinity 
```
