#!/usr/bin/env bash

CMD="palletgen -m single_pallet scenes/one_pallet.blend"
LOGFILE="palletgen_runs.log"

count=0

echo "=== Starting infinite palletgen loop ==="
echo "Log file: $LOGFILE"
echo "----------------------------------------"

while true; do
    count=$((count + 1))
    
    start_time=$(date +"%Y-%m-%d %H:%M:%S")
    start_secs=$(date +%s)
    
    echo "[$start_time] Run #$count started" | tee -a "$LOGFILE"
    
    # Run the actual command
    $CMD
    
    end_time=$(date +"%Y-%m-%d %H:%M:%S")
    end_secs=$(date +%s)
    
    duration=$((end_secs - start_secs))
    
    echo "[$end_time] Run #$count ended   (duration: ${duration}s)" | tee -a "$LOGFILE"
    echo "--------------------------------------------------------" | tee -a "$LOGFILE"
    
    # Optional: short sleep so logs don’t explode
    # sleep 1
done
