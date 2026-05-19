#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const skillName = "china-tax-calculator";
const repoRoot = path.resolve(__dirname, "..");
const sourceDir = path.join(repoRoot, skillName);

function usage() {
  console.log(`Usage:
  add [--force] [--dest <skills-dir>]

Installs ${skillName} into:
  \${CODEX_HOME:-$HOME/.codex}/skills/${skillName}

Examples:
  npx --yes --package github:haoyang9804/tax_calculator_skill_for_Chinese_Mainlander add
  npx --yes --package github:haoyang9804/tax_calculator_skill_for_Chinese_Mainlander add --force
`);
}

function parseArgs(argv) {
  const options = {
    force: false,
    destRoot: path.join(process.env.CODEX_HOME || path.join(os.homedir(), ".codex"), "skills"),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "add") {
      continue;
    }
    if (arg === "--force") {
      options.force = true;
      continue;
    }
    if (arg === "--dest") {
      const dest = argv[index + 1];
      if (!dest) {
        throw new Error("--dest requires a directory path");
      }
      options.destRoot = path.resolve(dest);
      index += 1;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return options;
}

function copyDirectory(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDirectory(srcPath, destPath);
    } else if (entry.isSymbolicLink()) {
      fs.symlinkSync(fs.readlinkSync(srcPath), destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const destDir = path.join(options.destRoot, skillName);

  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Cannot find bundled skill directory: ${sourceDir}`);
  }

  fs.mkdirSync(options.destRoot, { recursive: true });

  if (fs.existsSync(destDir)) {
    if (!options.force) {
      console.log(`${skillName} is already installed at ${destDir}`);
      console.log("Use --force to replace it.");
      return;
    }
    fs.rmSync(destDir, { recursive: true, force: true });
  }

  copyDirectory(sourceDir, destDir);
  console.log(`Installed ${skillName} to ${destDir}`);
  console.log("Restart Codex to pick up the new skill.");
}

try {
  main();
} catch (error) {
  console.error(`add: ${error.message}`);
  console.error("");
  usage();
  process.exit(1);
}
