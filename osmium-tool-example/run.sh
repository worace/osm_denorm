#!/usr/bin/env bash

set -euo pipefail

osmium export $1 -f geojsonseq -c config.json -i dense_file_array
