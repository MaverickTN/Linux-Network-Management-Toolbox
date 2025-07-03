# ❓ LNMT Troubleshooting Guide

This comprehensive troubleshooting guide helps you diagnose and resolve common issues with LNMT.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Training Problems](#training-problems)
- [Inference Issues](#inference-issues)
- [Performance Problems](#performance-problems)
- [Memory and Resource Issues](#memory-and-resource-issues)
- [Deployment Issues](#deployment-issues)
- [Data Loading Problems](#data-loading-problems)
- [GPU and Hardware Issues](#gpu-and-hardware-issues)
- [API and Integration Issues](#api-and-integration-issues)
- [Logging and Debugging](#logging-and-debugging)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### System Health Check

Run this diagnostic script to quickly identify common issues:

```python
import lnmt
import torch
import sys
import os

def run_diagnostics():
    print("🔍 LNMT System Diagnostics")
    print("=" * 50)
    
    # Python version
    print(f"Python Version: {sys.version}")
    
    # LNMT version
    try:
        print(f"LNMT Version: {lnmt.__version__}")
    except AttributeError:
        print("❌ LNMT version not found - installation may be incomplete")
    
    # PyTorch version and CUDA
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    
    # Memory information
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            total = torch.cuda.get_device_properties(i).total_memory / 1e9
            print(f"  GPU {i} Memory: {total:.1f} GB")
    
    # Environment variables
    print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
    
    # Test basic functionality
    try:
        model = lnmt.Model('bert-base-uncased')
        print("✅ Basic model loading works")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
    
    print("Diagnostics complete!")

if __name__ == "__main__":
    run_diagnostics()
```

### Quick CLI Check

```bash
# Check LNMT installation
lnmt --version

# Check system status
lnmt status

# List available models
lnmt models list --limit 5

# Test GPU detection
python -c "import lnmt; print('GPU Available:', lnmt.gpu.is_available())"
```

---

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'lnmt'`

**Symptoms:**
```
ImportError: No module named 'lnmt'
ModuleNotFoundError: No module named 'lnmt'
```

**Solutions:**

1. **Verify Installation**:
```bash
pip list | grep lnmt
```

2. **Reinstall LNMT**:
```bash
pip uninstall lnmt
pip install lnmt
```

3. **Check Python Environment**:
```bash
which python
which pip
python -c "import sys; print(sys.path)"
```

4. **Virtual Environment Issues**:
```bash
# Activate your virtual environment first
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install lnmt
```

### Issue: CUDA Installation Problems

**Symptoms:**
```
RuntimeError: CUDA out of memory
CUDA driver version is insufficient
No CUDA-capable device is detected
```

**Solutions:**

1. **Check CUDA Installation**:
```bash
nvidia-smi
nvcc --version
```

2. **Install Correct PyTorch Version**:
```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# For CPU only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

3. **Verify CUDA in Python**:
```python
import torch
print(torch.cuda.is_available())
print(torch.version.cuda)
```

### Issue: Dependency Conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently consider all the packages
DistributionNotFound: The 'transformers>=4.20' distribution was not found
```

**Solutions:**

1. **Clean Installation**:
```bash
pip uninstall lnmt torch transformers
pip install lnmt
```

2. **Use Fresh Environment**:
```bash
python -m venv fresh_env
source fresh_env/bin/activate
pip install lnmt
```

3. **Install with Specific Versions**:
```bash
pip install lnmt==1.2.0 torch==2.0.1 transformers==4.30.0
```

---

## Training Problems

### Issue: Training Crashes with Out of Memory

**Symptoms:**
```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solutions:**

1. **Reduce Batch Size**:
```python
trainer = lnmt.Trainer(
    model=model,
    batch_size=8,  # Reduce from 32
    gradient_accumulation_steps=4  # Maintain effective batch size
)
```

2. **Enable Gradient Checkpointing**:
```python
model = lnmt.Model('bert-large-uncased')
model.enable_gradient_checkpointing()
```

3. **Use Mixed Precision**:
```python
trainer = lnmt.Trainer(
    model=model,
    precision='fp16',  # or 'bf16'
    auto_scale_batch_size=True
)
```

4. **Clear GPU Cache**:
```python
import torch
torch.cuda.empty_cache()
```

### Issue: Training Loss Not Decreasing

**Symptoms:**
- Loss remains constant or increases
- Validation accuracy stays low
- Model appears not to learn

**Solutions:**

1. **Check Learning Rate**:
```python
# Try different learning rates
for lr in [1e-3, 1e-4, 1e-5, 2e-5]:
    trainer = lnmt.Trainer(model, learning_rate=lr)
    # Test for a few epochs
```

2. **Verify Data Loading**:
```python
# Check your data
dataset = lnmt.Dataset.from_jsonl('train.jsonl')
print(f"Dataset size: {len(dataset)}")
print(f"Sample: {dataset[0]}")

# Check labels
labels = [item['label'] for item in dataset[:100]]
print(f"Unique labels: {set(labels)}")
```

3. **Debug Training Step**:
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

trainer = lnmt.Trainer(model, log_every=1)
trainer.fit(train_data, max_epochs=1)  # Train for 1 epoch to debug
```

4. **Check Model Architecture**:
```python
# Verify model setup
model = lnmt.Model('bert-base-uncased')
print(model)
print(f"Model parameters: {sum(p.numel() for p in model.parameters())}")
```

### Issue: Training Extremely Slow

**Symptoms:**
- Training takes much longer than expected
- Low GPU utilization
- High CPU usage but low GPU usage

**Solutions:**

1. **Optimize Data Loading**:
```python
dataloader = lnmt.DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,          # Increase workers
    pin_memory=True,        # Enable for GPU
    prefetch_factor=2,      # Prefetch batches
    persistent_workers=True # Reuse workers
)
```

2. **Profile Training**:
```python
# Use PyTorch profiler
with torch.profiler.profile(
    activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
    record_shapes=True
) as prof:
    trainer.fit(train_data, max_epochs=1)

print(prof.key_averages().table(sort_by="cuda_time_total"))
```

3. **Check Disk I/O**:
```bash
# Monitor disk usage
iostat -x 1  # Linux
# or
Resource Monitor  # Windows
```

---

## Inference Issues

### Issue: Slow Inference Performance

**Symptoms:**
- High latency per request
- Low throughput
- Poor response times

**Solutions:**

1. **Enable Model Optimization**:
```python
# Compile model (PyTorch 2.0+)
model = lnmt.Model.load('my-model')
model.compile(mode='max-autotune')

# Enable caching
model.enable_cache(cache_type='memory', max_size='1GB')
```

2. **Use Batch Inference**:
```python
# Process multiple inputs together
inputs = ["text 1", "text 2", "text 3"]
predictions = model.predict(inputs, batch_size=32)
```

3. **Quantization**:
```python
# Quantize model for faster inference
quantized_model = lnmt.quantize(
    model,
    method='dynamic',
    dtype='int8'
)
```

### Issue: Inconsistent Predictions

**Symptoms:**
- Different results for same input
- Unstable model behavior
- Random-looking outputs

**Solutions:**

1. **Set Random Seeds**:
```python
import torch
import random
import numpy as np

def set_seed(seed=42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True

set_seed(42)
```

2. **Check Model Mode**:
```python
# Ensure model is in evaluation mode
model.eval()

# Disable dropout for inference
with torch.no_grad():
    predictions = model.predict(inputs)
```

3. **Verify Input Preprocessing**:
```python
# Check tokenization consistency
tokenizer = model.tokenizer
inputs = ["same text", "same text"]
tokens1 = tokenizer(inputs[0])
tokens2 = tokenizer(inputs[1])
assert tokens1 == tokens2, "Tokenization inconsistency"
```

---

## Performance Problems

### Issue: Low GPU Utilization

**Symptoms:**
```bash
# nvidia-smi shows low GPU usage
GPU-Util: 15%
Memory-Usage: 2048MiB / 24564MiB
```

**Solutions:**

1. **Increase Batch Size**:
```python
# Find optimal batch size
trainer = lnmt.Trainer(
    model,
    batch_size=64,  # Increase until memory limit
    auto_scale_batch_size='binsearch'
)
```

2. **Optimize Data Pipeline**:
```python
# Reduce data loading bottleneck
dataloader = lnmt.DataLoader(
    dataset,
    num_workers=8,      # More workers
    pin_memory=True,    # Faster GPU transfer
    drop_last=True      # Consistent batch sizes
)
```

3. **Profile Bottlenecks**:
```python
import time

# Time different components
start = time.time()
batch = next(iter(dataloader))
print(f"Data loading: {time.time() - start:.3f}s")

start = time.time()
outputs = model(batch)
print(f"Forward pass: {time.time() - start:.3f}s")
```

### Issue: Memory Leaks

**Symptoms:**
- Memory usage increases over time
- Eventually runs out of memory
- System becomes unresponsive

**Solutions:**

1. **Clear Variables**:
```python
import gc

# Clear variables and cache
del model, trainer, dataset
gc.collect()
torch.cuda.empty_cache()
```

2. **Use Context Managers**:
```python
# Proper resource management
with torch.no_grad():
    predictions = model.predict(inputs)

# Clear intermediate results
torch.cuda.empty_cache()
```

3. **Monitor Memory Usage**:
```python
import psutil
import torch

def print_memory_usage():
    if torch.cuda.is_available():
        print(f"GPU Memory: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"RAM Usage: {psutil.virtual_memory().percent}%")

# Call periodically during training
print_memory_usage()
```

---

## Memory and Resource Issues

### Issue: CPU Memory Exhaustion

**Symptoms:**
```
MemoryError: Unable to allocate array
RuntimeError: DefaultCPUAllocator: not enough memory
```

**Solutions:**

1. **Reduce Data Loading Workers**:
```python
dataloader = lnmt.DataLoader(
    dataset,
    num_workers=2,  # Reduce from higher number
    batch_size=16   # Also reduce batch size
)
```

2. **Use Streaming Dataset**:
```python
# For large datasets
dataset = lnmt.StreamingDataset('large_file.jsonl')
```

3. **Monitor Memory Usage**:
```bash
# Linux
htop
free -h

# Mac
top
activity monitor

# Windows
Task Manager
```

### Issue: Disk Space Problems

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**

1. **Clean Model Cache**:
```bash
# Clear downloaded models
rm -rf ~/.cache/lnmt/
# or
lnmt cache clear
```

2. **Set Custom Cache Directory**:
```python
# Use different location
model = lnmt.Model('bert-base-uncased', cache_dir='/path/to/large/disk')
```

3. **Monitor Disk Usage**:
```bash
df -h  # Check disk usage
du -sh ~/.cache/lnmt/  # Check LNMT cache size
```

---

## Deployment Issues

### Issue: Kubernetes Deployment Fails

**Symptoms:**
```
pod has unbound immediate PersistentVolumeClaims
ImagePullBackOff
CrashLoopBackOff
```

**Solutions:**

1. **Check Resource Limits**:
```yaml
# deployment.yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

2. **Verify Image**:
```bash
# Check if image exists
docker pull your-registry/lnmt:latest

# Check image details
docker inspect your-registry/lnmt:latest
```

3. **Debug Pod Issues**:
```bash
# Check pod status
kubectl get pods

# Get pod logs
kubectl logs <pod-name>

# Describe pod for events
kubectl describe pod <pod-name>
```

### Issue: API Server Not Responding

**Symptoms:**
- Connection timeouts
- 500 Internal Server Error
- No response from server

**Solutions:**

1. **Check Server Logs**:
```bash
# Docker logs
docker logs <container-name>

# Kubernetes logs
kubectl logs deployment/lnmt-inference

# Local server logs
tail -f /var/log/lnmt/server