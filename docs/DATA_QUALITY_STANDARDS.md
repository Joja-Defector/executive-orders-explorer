# Executive Orders Scraper: Data Quality Standards

This document outlines the data quality standards and checks implemented for the Executive Orders scraper project.

## Overview

The data quality checking system ensures that the scraped executive orders data meets established quality criteria before being committed to the repository. Quality checks are automatically run as part of the GitHub Actions workflow after each scraping operation.

## Quality Check Categories

### 1. Missing Values

Checks for missing data in critical columns:
- `title`: The title of the executive order
- `link`: The URL to the executive order
- `date`: The publication date
- `content`: The full text content

**Threshold:** No more than 10% missing values in any critical column.

### 2. Data Format Validation

Ensures data adheres to expected formats:
- URLs must be valid White House website URLs (`https://www.whitehouse.gov/...`)
- Dates must be in a recognizable format
- Content must not contain error messages or HTML fragments

**Threshold:** No more than 10% of records can have format issues.

### 3. Duplicate Detection

Identifies and flags duplicate records:
- Exact duplicates (entire row is identical)
- Duplicate links (same URL, different metadata)
- Duplicate titles with different links (potential inconsistencies)

**Threshold:** No duplicates should exist in the final dataset.

### 4. Content Quality

Evaluates the quality of the scraped content:
- Content length distribution (average, minimum, maximum)
- Detection of very short content (<200 characters)
- Presence of HTML tags in content
- Excessive whitespace or formatting issues

**Threshold:** No more than 15% of records can have content quality issues.

### 5. Data Recency

Checks if the dataset includes recent records:
- Identifies the most recent record date
- Alerts if no recent data has been added within the past 14 days
- Fails if no data from the past 30 days is present

## Overall Quality Score

The overall data quality score is calculated as the percentage of check categories that pass:
- 5/5 (100%): Excellent quality
- 4/5 (80%): Good quality
- 3/5 (60%): Marginal quality
- <60%: Poor quality

**Threshold for Action:** Data changes are only committed if the quality score is at least 80% (4 out of 5 checks pass).

## Error Handling

When quality checks fail:
1. Changes are not committed to the repository
2. A GitHub issue is automatically created to alert maintainers
3. Detailed logs are available in the GitHub Actions workflow output

## Manual Review Process

In cases where automated checks fail but the data is still valuable:
1. Review the data quality report and logs
2. Determine the cause of quality issues
3. If appropriate, manually commit the changes with clear documentation of known issues
4. Update quality thresholds or checks if needed for special cases

## Continuous Improvement

The data quality framework should be regularly reviewed and updated:
- Adjust thresholds based on accumulated knowledge about typical data patterns
- Add new check categories as additional quality concerns are identified
- Refine existing checks to reduce false positives/negatives