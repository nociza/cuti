# Using the Gemini CLI for Codebase Analysis

When you need to analyze, document, or refactor code, the Gemini command-line interface (CLI) is a powerful tool. It allows you to reference local files and directories directly in your prompt, which is perfect for tasks involving a single file, multiple components, or even an entire project.

The primary command for this is  **`gemini -p`** , which leverages Google Gemini's large context capacity.

---

## File and Directory Syntax

You can include files and directories in your prompts using the **`@`** symbol followed by the path. These paths are  **relative to the directory where you run the `gemini` command** .

### Examples

* **Single file analysis:**
  **Bash**

  ```
  gemini -p "@app/main.py Explain this file's purpose and structure."
  ```
* **Multiple files:**
  **Bash**

  ```
  gemini -p "@config.yml @app/services/api_client.rb Analyze how the configuration is used by the API client."
  ```
* **Entire directory:**
  **Bash**

  ```
  gemini -p "@lib/ Summarize the core utilities provided in this library."
  ```
* **Multiple directories:**
  **Bash**

  ```
  gemini -p "@src/ @tests/ Analyze the test coverage for the source code."
  ```
* **Current directory and all subdirectories:**
  **Bash**

  ```
  gemini -p "@./ Give me an overview of this entire project."
  ```

  Alternatively, you can use the **`--all_files`** flag to include everything in the current directory and its subdirectories:

  **Bash**

  ```
  gemini --all_files -p "Analyze the project structure and dependencies."
  ```

---

## Common Use Cases & Example Prompts

Here are some common ways to use the Gemini CLI for codebase tasks.

### High-Level Understanding

* **Architecture Summary:** Get a bird's-eye view of your project.
  **Bash**

  ```
  gemini -p "@app/ @lib/ Summarize the architecture of this codebase and explain how the 'app' and 'lib' directories interact."
  ```
* **Dependency Analysis:** Understand the project's third-party libraries.
  **Bash**

  ```
  gemini -p "@package.json @requirements.txt @Gemfile Analyze the dependencies and identify any potential version conflicts or security vulnerabilities."
  ```

### Implementation, Refactoring, and Verification

* **Verify a Feature:** Check if a feature is implemented and where.
  **Bash**

  ```
  gemini -p "@src/ Has a dark mode been implemented? Show me the relevant files and functions."
  ```
* **Audit for Security:** Look for specific security practices.
  **Bash**

  ```
  gemini -p "@app/controllers/ Are there protections against SQL injection? Show how user inputs are sanitized before database queries."
  ```
* **Find Code to Refactor:** Identify complex or outdated code.
  **Bash**

  ```
  gemini -p "@app/helpers/ Review this directory and suggest areas that could be refactored for better readability or performance."
  ```
* **Modernize Code:** Update code to use newer language features.
  **Bash**

  ```
  gemini -p "@app/utils.js Convert the Promise-based functions in this file to use async/await syntax."
  ```

### Documentation and Onboarding

* **Generate a README:** Create project documentation automatically.
  **Bash**

  ```
  gemini --all_files -p "Generate a comprehensive README.md for this project, explaining its purpose, how to set it up, and how to run it."
  ```
* **Explain a Complex Module:** Simplify complex code for new team members.
  **Bash**

  ```
  gemini -p "@app/modules/billing/ Explain this billing module in simple terms for a new developer joining the team."
  ```

### Testing

* **Generate Unit Tests:** Create test cases for existing code.
  **Bash**

  ```
  gemini -p "@lib/validators.go Write unit tests for all functions in this file using the standard 'testing' package."
  ```
* **Analyze Test Coverage:** Identify untested code paths.
  **Bash**

  ```
  gemini -p "@src/ @tests/ Based on the code in 'src' and the tests in 'tests', what critical features seem to be untested?"
  ```

---

## Important Notes

* **Relative Paths:** Remember that paths using the `@` syntax are relative to your current working directory.
* **Full Context:** The CLI includes the full contents of the specified files in the prompt, giving Gemini complete context for its analysis.
* **Large Context Window:** Gemini's ability to handle a large context window is a key advantage, enabling true project-wide analysis that is difficult with other tools.
* **Be Specific:** The more specific your question is, the more accurate and helpful the answer will be. Provide clear instructions on what you want Gemini to do.
