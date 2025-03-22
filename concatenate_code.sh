#!/bin/bash

# File: concatenate_code.sh
# This script concatenates all files from the 'fin_statement_model' directory into a single file,
# 'combined_code.txt'. Each file's content is preceded by a header indicating the file name.

OUTPUT_FILE="combined_code.txt"

# Clear the output file if it exists
: > "${OUTPUT_FILE}"

# Iterate over all files in the fin_statement_model directory recursively
find fin_statement_model -type f | while IFS= read -r file; do
    # Skip the output file itself in case it's inside the directory
    if [[ "$file" == *"${OUTPUT_FILE}"* ]]; then
        continue
    fi
    echo "===== ${file} =====" >> "${OUTPUT_FILE}"
    cat "$file" >> "${OUTPUT_FILE}"
    echo -e "\n" >> "${OUTPUT_FILE}"
done

echo "All code concatenated into ${OUTPUT_FILE}" 