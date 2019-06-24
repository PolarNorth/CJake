workon common
python analisys_tool.py -c -a > outputs/only_C_and_alternatives.txt
python analisys_tool.py -c > outputs/only_C_and_no_alternatives.txt
python analisys_tool.py -a > outputs/not_C_and_alternatives.txt
python analisys_tool.py > outputs/not_C_and_no_alternatives.txt
touch outputs/short_results
echo "C style and process alternatives: " > outputs/short_results
tail -1 outputs/only_C_and_alternatives.txt >> outputs/short_results
echo "C style and don't process alternatives: " >> outputs/short_results
tail -1 outputs/only_C_and_no_alternatives.txt >> outputs/short_results
echo "Process all structures and process alternatives: " >> outputs/short_results
tail -1 outputs/not_C_and_alternatives.txt >> outputs/short_results
echo "Process all structures and don't process alternatives: " >> outputs/short_results
tail -1 outputs/not_C_and_no_alternatives.txt >> outputs/short_results