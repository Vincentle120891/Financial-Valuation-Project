#!/usr/bin/env node

/**
 * COMPONENT PROP VALIDATION AUDIT
 * 
 * Scans all React components and identifies:
 * 1. Components WITHOUT PropTypes (need to be added)
 * 2. Components WITH PropTypes (already compliant)
 * 
 * Run: node frontend/scripts/audit-props.js
 */

const fs = require('fs');
const path = require('path');

const COMPONENTS_DIR = path.join(__dirname, '../src/components');

const results = {
  withoutPropTypes: [],
  withPropTypes: [],
};

function scanFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const fileName = path.relative(COMPONENTS_DIR, filePath);

    // Check if PropTypes is imported
    const hasPropTypesImport = content.includes("import PropTypes from 'prop-types'") 
      || content.includes('import PropTypes from "prop-types"');
    
    // Check if PropTypes is used
    const hasPropTypesAssignment = /\.propTypes\s*=/.test(content);

    // Check if component accepts props
    const hasProps = /const\s+\w+\s*=\s*\({/.test(content) || 
                    /function\s+\w+\s*\({/.test(content);

    if (hasProps) {
      if (hasPropTypesImport && hasPropTypesAssignment) {
        results.withPropTypes.push(fileName);
      } else {
        results.withoutPropTypes.push(fileName);
      }
    }
  } catch (err) {
    console.error(`Error reading ${filePath}:`, err.message);
  }
}

function walkDir(dir) {
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat.isDirectory()) {
      walkDir(filePath);
    } else if (file.endsWith('.jsx') || file.endsWith('.tsx')) {
      scanFile(filePath);
    }
  });
}

console.log('🔍 Scanning components for PropTypes compliance...\n');

walkDir(COMPONENTS_DIR);

console.log('✅ COMPONENTS WITH PropTypes VALIDATION:');
results.withPropTypes.forEach(f => console.log(`  ✓ ${f}`));
console.log(`   Total: ${results.withPropTypes.length}\n`);

console.log('❌ COMPONENTS WITHOUT PropTypes VALIDATION:');
results.withoutPropTypes.forEach(f => console.log(`  ✗ ${f}`));
console.log(`   Total: ${results.withoutPropTypes.length}\n`);

console.log('📊 SUMMARY:');
console.log(`   Compliant: ${results.withPropTypes.length}`);
console.log(`   Need updates: ${results.withoutPropTypes.length}`);
if (results.withPropTypes.length + results.withoutPropTypes.length > 0) {
  const rate = Math.round(results.withPropTypes.length / (results.withPropTypes.length + results.withoutPropTypes.length) * 100);
  console.log(`   Compliance rate: ${rate}%`);
}
