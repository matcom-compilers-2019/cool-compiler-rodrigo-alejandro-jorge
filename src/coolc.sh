INPUT_FILE=$1
OUTPUT_FILE=${INPUT_FILE:0: -2}mips

echo "Terrible, oremos"
echo "Copyright (c) 2019: Jorge Igancio Rodríguez de la Vega Castro, Rodrigo Sua García Eternod, Alejandro Rodríguez Pérez"

echo "Compiling $INPUT_FILE into $OUTPUT_FILE"
python main.py $INPUT_FILE

