# CaseWare IDEA Workflow Builder

A powerful workflow automation tool for CaseWare IDEA that chains field operations, database operations, and multi-database joins for financial data analysis and reconciliation.

## Features

### Core Capabilities
- **Multi-Database Joins**: Join GL → TB → Bank statements on common keys
- **Sequential Operations**: Chain up to 5 operations with result passing
- **Field Transformations**: Clean, format, and transform data
- **Custom Regex**: Pattern matching and replacement
- **Workflow Persistence**: Save and load workflows for reuse
- **Error Handling**: Comprehensive logging and failure tracking
- **Execution Preview**: See what will run before executing

### Supported Operations

#### Field Operations
| Operation | Syntax | Example | Purpose |
|-----------|--------|---------|---------|
| @TRIM | @TRIM(field) | - | Remove leading/trailing spaces |
| @UPPER | @UPPER(field) | - | Convert to uppercase |
| @LOWER | @LOWER(field) | - | Convert to lowercase |
| @LEFT | @LEFT(field,n) | `5` | Extract leftmost n characters |
| @RIGHT | @RIGHT(field,n) | `3` | Extract rightmost n characters |
| @MID | @MID(field,start,len) | `2,4` | Extract substring |
| @ABS | @ABS(field) | - | Absolute value |
| @ROUND | @ROUND(field,decimals) | `2` | Round to decimals |
| @INT | @INT(field) | - | Integer part |
| @YEAR | @YEAR(field) | - | Extract year from date |
| @MONTH | @MONTH(field) | - | Extract month from date |
| @DAY | @DAY(field) | - | Extract day from date |

#### Database Operations
| Operation | Parameters | Example | Purpose |
|-----------|------------|---------|---------|
| JOIN | foreignDB,foreignKey | `TB.IMD,ACCOUNT` | Join databases on matching keys |
| EXTRACT | criteria | `AMOUNT > 1000` | Filter records by criteria |
| SORT | field,A/D | `ACCOUNT,A` | Sort ascending (A) or descending (D) |
| SUMMARIZE | field | - | Summarize by field |
| INDEX | field | - | Create index on field |

#### Custom Operations
| Operation | Parameters | Example | Purpose |
|-----------|------------|---------|---------|
| REGEX | pattern,replacement | `^\d{4},ACCT-` | Match pattern and replace |
| FILLDOWN | - | - | Fill blank cells with value above |
| APPEND | database | `PREVIOUS_PERIOD.IMD` | Combine databases vertically |

## Usage Guide

### Basic Workflow

1. **Select Source Database**
   - Choose current database or browse for specific file
   - Fields will auto-populate

2. **Configure Steps**
   - Select operation type
   - Choose field to operate on
   - Enter parameters
   - Name the output (e.g., RESULT1)
   - Check "Active" to enable step

3. **Preview**
   - Click "Preview" to see execution plan
   - Verify operations and parameters

4. **Execute**
   - Click "Execute" to run workflow
   - Monitor execution log for status

5. **Save for Reuse**
   - Click "Save Flow" to save workflow
   - Load later with "Load Flow"

### Common Workflows

#### Example 1: Multi-Database Reconciliation
Join GL to Trial Balance to Bank Statement, then extract variances:

```
Step 1: JOIN
  Field: ACCOUNT_NUMBER
  Params: TB.IMD,ACCOUNT
  Output: GL_TB
  Active: ✓

Step 2: JOIN
  Field: ACCOUNT_NUMBER
  Params: BANK.IMD,ACCT_NUM
  Output: FULL_RECON
  Active: ✓

Step 3: EXTRACT
  Params: @ABS(GL_AMOUNT - BANK_AMOUNT) > 0.01
  Output: VARIANCES
  Active: ✓
```

#### Example 2: Account Number Cleanup
Clean and standardize account numbers:

```
Step 1: @TRIM
  Field: ACCOUNT
  Output: CLEAN_ACCT
  Active: ✓

Step 2: @UPPER
  Field: CLEAN_ACCT
  Output: UPPER_ACCT
  Active: ✓

Step 3: REGEX
  Field: UPPER_ACCT
  Params: [^A-Z0-9],
  Output: FINAL_ACCT
  Active: ✓
```

#### Example 3: Period Analysis
Extract and analyze by period:

```
Step 1: @YEAR
  Field: TRANS_DATE
  Output: YEAR_FIELD
  Active: ✓

Step 2: @MONTH
  Field: TRANS_DATE
  Output: MONTH_FIELD
  Active: ✓

Step 3: EXTRACT
  Params: YEAR_FIELD = 2024 AND MONTH_FIELD >= 10
  Output: Q4_2024
  Active: ✓

Step 4: SUMMARIZE
  Field: ACCOUNT
  Output: Q4_SUMMARY
  Active: ✓
```

### Variable Substitution

Use output from previous steps as input to later steps:

```
Step 1: JOIN → Output: RESULT1
Step 2: EXTRACT
  Params: Use {RESULT1} in criteria
  The system automatically resolves {RESULT1} to the database path
```

### JOIN Operation Details

**Single Join:**
```
Operation: JOIN
Field: ACCOUNT_NUMBER (primary key in source DB)
Database: Select foreign database from dropdown
Params: FOREIGN_KEY_FIELD
```

**Multi-Join (Chain JOINs):**
```
Step 1: JOIN GL to TB
  Field: ACCT
  Params: TB.IMD,ACCOUNT
  Output: STEP1_RESULT

Step 2: JOIN STEP1_RESULT to Bank
  Field: ACCT
  Params: BANK.IMD,ACCT_NUM
  Output: FINAL_RESULT
```

### REGEX Operation

**Pattern Matching:**
```
REGEX
  Field: ACCOUNT
  Params: ^\d{4},
  Output: MATCHED
```

**Pattern Replacement:**
```
REGEX
  Field: ACCOUNT
  Params: [^0-9],-
  Output: CLEANED
```

## Tips for Financial Data Analysis

### Account Reconciliation
1. Start with @TRIM to clean data
2. JOIN databases on account keys
3. EXTRACT differences > materiality threshold
4. SORT by variance amount descending

### Data Validation
1. Use REGEX to validate account formats
2. EXTRACT records that don't match pattern
3. Create exception reports

### Period-End Procedures
1. Save workflows for monthly close
2. Use variable substitution for dynamic dates
3. SUMMARIZE for management reports

### Performance
- Use EXTRACT early to reduce dataset size
- INDEX fields used in JOIN operations
- Chain operations to avoid intermediate files

## Troubleshooting

### Common Issues

**"Cannot open database"**
- Verify database path is correct
- Check file exists in working directory
- Use Browse (...) button to select file

**"Step X: ✗ FAILED"**
- Check execution log for details
- Verify field names match database
- Confirm parameters are correct for operation

**JOIN fails**
- Ensure key fields exist in both databases
- Verify field names are spelled correctly
- Check data types match

**REGEX not working**
- IDEA may not support @RegexReplace in all versions
- Consider using EXTRACT with pattern matching instead
- Test regex pattern separately first

### Best Practices

1. **Preview First**: Always preview before executing
2. **Save Often**: Save working workflows
3. **Test with Small Data**: Test on subset first
4. **Name Outputs Clearly**: Use descriptive result names
5. **Document Parameters**: Add comments in workflow name
6. **Check Execution Log**: Verify each step succeeded

## File Format

Workflows are saved as `.wf` files in the working directory with format:
```
WORKFLOW v1.0
[source_database_path]
[step1_data]
[step2_data]
...
```

## Version History

**v1.0** - Initial release
- 5-step workflow builder
- 20 operation types
- Multi-database join support
- Workflow save/load
- Execution preview and logging
- Variable substitution
- Comprehensive error handling

## Support

For CaseWare IDEA documentation:
- IDEA Help > Scripting Guide
- IDEA Function Reference
- CaseWare Community Forums

## License

This script is provided as-is without warranties. Test thoroughly before use in production environments.
