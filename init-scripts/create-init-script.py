script = '''#!/bin/bash

# SET VARIABLES
WORKSPACE_ID=11111111111111
WORKSPACE_URL=adb-111111111111.11.azuredatabricks.net
MRAN_SNAPSHOT=2022-09-08
SF_ACCOUNT=123123123123123123

if [[ $DB_IS_DRIVER = "TRUE" ]]; then
  
  # install unixodb
  sudo apt-get update
  sudo apt-get install unixodbc -y

  # install simba spark odbc driver [CHANGE FROM https://www.databricks.com/spark/odbc-drivers-archive]
  curl -o \
    /tmp/odbc-driver.zip \
    https://databricks-bi-artifacts.s3.us-east-2.amazonaws.com/simbaspark-drivers/odbc/2.6.26/SimbaSparkODBC-2.6.26.1045-Debian-64bit.zip
    
  unzip /tmp/odbc-driver.zip -d /tmp/odbc-simba/
  sudo apt-get install libsasl2-modules-gssapi-mit -y
  sudo dpkg -i /tmp/odbc-simba/simbaspark_2.6.26.1045-2_amd64.deb
  
  # install Snowflake odbc driver
  curl -o \
  /tmp/sf-odbc-driver.deb \
  https://sfc-repo.snowflakecomputing.com/odbc/linux/2.25.7/snowflake-odbc-2.25.7.x86_64.deb

  sudo dpkg -i /tmp/sf-odbc-driver.deb

  # configure odbc
  echo """
[ODBC Data Sources]
databricks=Databricks ODBC Connector

[databricks-self]
Driver          = /opt/simba/spark/lib/64/libsparkodbc_sb64.so
host            = ${WORKSPACE_URL}
port            = 443
SparkServerType = 3
Schema          = default
ThriftTransport = 2
SSL             = 1
AuthMech        = 3
UID             = token
HTTPPath        = sql/protocolv1/o/${WORKSPACE_ID}/${DB_CLUSTER_ID}

[databricks]
Driver          = /opt/simba/spark/lib/64/libsparkodbc_sb64.so
host            = ${WORKSPACE_URL}
port            = 443
SparkServerType = 3
Schema          = default
ThriftTransport = 2
SSL             = 1
AuthMech        = 3
UID             = token

[snowflake]
Description.    = SnowflakeDB
Driver          = SnowflakeDSIIDriver
Locale          = en-US
SERVER          = ${SF_ACCOUNT}.snowflakecomputing.com
PORT            = 443
SSL             = on
ACCOUNT         = ${SF_ACCOUNT}

  """ > /etc/odbc.ini

  # configure mlflow
  echo """
MLFLOW_PYTHON_BIN="/databricks/python/bin/python3"
MLFLOW_BIN="/databricks/python3/bin/mlflow"
RETICULATE_PYTHON="/databricks/python3/bin/python3"
  """ >> /etc/R/Renviron.site

  # configure reticulate
  echo "PATH=${PATH}:/databricks/conda/bin" >> /usr/lib/R/etc/Renviron.site
  
  # install mlflow and ODBC as of MRAN snapshot appropriate to DBR
  Rscript -e "install.packages(c('mlflow', 'odbc'), repos='https://cran.microsoft.com/snapshot/${MRAN_SNAPSHOT}/')"

  # RStudio connection pane configs
  mkdir /etc/rstudio/connections
  echo """library(DBI)
con <- dbConnect(
  odbc::odbc(),
  dsn = 'databricks-self',
  PWD = \${0:Password/Token=sparkR.conf('USER_TOKEN')}
)
  """ > /etc/rstudio/connections/'ODBC to RStudio Cluster Spark Session.R'

  echo """library(DBI)
con <- dbConnect(
  odbc::odbc(),
  dsn = 'databricks',
  HTTPPath = '\${0:HTTPPath=\"\"}'
  PWD = \${1:Password/Token=sparkR.conf('USER_TOKEN')}
)
  """ >> /etc/rstudio/connections/'Databricks ODBC.R'

  echo """install.packages(c("DBI", "dplyr","dbplyr","odbc"))
library(DBI)
library(dplyr)
library(dbplyr)
library(odbc)
myconn <- DBI::dbConnect(
  odbc::odbc(), 
  dsn="snowflake", 
  uid='\${0:uid=USERNAME}', 
  pwd='\${1:pwd=Snowflak123}')
  """ >> /etc/rstudio/connections/'snowflake.R'

fi
'''

dbutils.fs.mkdirs("/databricks/init/na")
dbutils.fs.put("/databricks/init/na/r-env-init.sh", script, True)
