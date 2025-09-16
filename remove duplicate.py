#!/usr/bin/env python3
"""
Script to remove duplicate lines from a text file while preserving order.
The first occurrence of each line is kept, subsequent duplicates are removed.
"""

def remove_duplicate_lines(input_file, output_file):
    """
    Remove duplicate lines from input file and write unique lines to output file.
    
    Args:
        input_file (str): Path to input file
        output_file (str): Path to output file
    """
    seen_lines = set()
    unique_lines = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Strip whitespace for comparison but keep original line
                stripped_line = line.strip()
                
                if stripped_line not in seen_lines:
                    seen_lines.add(stripped_line)
                    unique_lines.append(line.rstrip('\n\r'))
                else:
                    print(f"Duplicate found at line {line_num}: {stripped_line[:50]}...")
        
        # Write unique lines to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in unique_lines:
                f.write(line + '\n')
        
        print(f"\nProcessing complete!")
        print(f"Original file had {line_num} lines")
        print(f"Output file has {len(unique_lines)} unique lines")
        print(f"Removed {line_num - len(unique_lines)} duplicate lines")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    # Configuration
    input_filename = "input.txt"
    output_filename = "output.txt"
    
    print("Duplicate Line Remover")
    print("=" * 30)
    print(f"Input file: {input_filename}")
    print(f"Output file: {output_filename}")
    print()
    
    # Allow user to specify custom filenames
    custom_input = input(f"Press Enter to use '{input_filename}' or type a different filename: ").strip()
    if custom_input:
        input_filename = custom_input
    
    custom_output = input(f"Press Enter to use '{output_filename}' or type a different filename: ").strip()
    if custom_output:
        output_filename = custom_output
    
    print(f"\nProcessing '{input_filename}'...")
    remove_duplicate_lines(input_filename, output_filename)

if __name__ == "__main__":
    main()