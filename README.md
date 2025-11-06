# Installation and Usage Guide

This project can automatically generate Playwright/Cypress automation scripts based on your test plan.

---

## 1. Install uv (Python Package Manager)

Please run the following command in your terminal to install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Install Python Dependencies

In the project root directory, execute the following command to install required dependencies locally:

```bash
uv sync
```

---

## 3. Node.js Version Requirement

Please ensure your Node.js version is **22 or higher**.  
It is recommended to use [nvm](https://github.com/nvm-sh/nvm) to manage and upgrade your Node.js version.

---

## 4. Project Parameter Configuration

Open the `main.py` file and adjust the following variables according to your requirements:

- `GOAL_LANGUAGE`: Choose the language and framework for the generated automation script. Supported options:
  - `'js-playwright'` (JavaScript)
  - `'python-playwright'` (Python)
  - `'cypress'` (JavaScript)
- `FEATURE_NAME`: Feature name (used to name the generated file).
- `GOAL`: Enter your test plan here. The system will automatically generate the corresponding test script based on this content.

---

## 5. Generate Automation Test Script

After adjusting the above variables, run the following command in your terminal:

```bash
uv run python main.py
```

After execution completes, the script will generate the corresponding automation test file in the `results/` directory based on `FEATURE_NAME` and `GOAL_LANGUAGE`.

---

For more settings or if you encounter issues, please refer to the source code comments or contact the hank.tsai@appier.com
