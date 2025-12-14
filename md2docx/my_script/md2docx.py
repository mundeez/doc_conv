import subprocess


working_directory = input("Enter the directory Location of the markdown file: ")
file_name_with_ext = input("Enter the name of the markdown file (with .md extension): ")
file_name = file_name_with_ext.split(".")[0] # Extract file name without extension
# print(file_name_with_ext)
# print(file_name)
# Convert Markdown to DOCX using Pandoc
conversion_shell = subprocess.run(f"pandoc -o {working_directory}/{file_name}.docx -f markdown -t docx {working_directory}/{file_name}.md", shell=True, capture_output=True, text=True)
if conversion_shell.returncode == 0:
    print(f"Conversion successful! The DOCX file is located at: {working_directory}/{file_name}.docx")
else:
    print("Conversion failed!")
    print("Error message:", conversion_shell.stderr)
