# 🚀 LNMT Quick Start Guide

Get up and running with LNMT in just 5 minutes! This guide will walk you through installation, basic usage, and your first model training.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed on your system
- **8GB+ RAM** (16GB+ recommended for larger models)
- **CUDA-compatible GPU** (optional but recommended for training)
- **Internet connection** for downloading pre-trained models

## 🔧 Installation

### Option 1: Install from PyPI (Recommended)

```bash
# Install the latest stable version
pip install lnmt

# Verify installation
lnmt --version
```

### Option 2: Install with GPU Support

```bash
# Install with CUDA support
pip install lnmt[gpu]

# Verify GPU detection
python -c "import lnmt; print(lnmt.gpu.is_available())"
```

### Option 3: Development Installation

```bash
# Clone and install from source
git clone https://github.com/your-org/lnmt.git
cd lnmt
pip install -e ".[dev]"
```

## 🏃‍♂️ 5-Minute Tutorial

### Step 1: Initialize Your First Project

```bash
# Create a new LNMT project
lnmt init my-first-project
cd my-first-project

# This creates:
# ├── config.yaml          # Project configuration
# ├── data/                # Training data directory
# ├── models/              # Model storage
# ├── notebooks/           # Jupyter notebooks
# └── scripts/             # Training scripts
```

### Step 2: Prepare Your Data

Create a simple text dataset:

```python
# create_sample_data.py
import json

# Sample training data
data = [
    {"text": "The weather is beautiful today.", "label": "positive"},
    {"text": "I love learning new technologies.", "label": "positive"},
    {"text": "This is a terrible experience.", "label": "negative"},
    {"text": "I'm frustrated with this process.", "label": "negative"},
]

# Save as JSONL format
with open('data/train.jsonl', 'w') as f:
    for item in data:
        f.write(json.dumps(item) + '\n')

print("Sample data created!")
```

```bash
python create_sample_data.py
```

### Step 3: Train Your First Model

```python
# train_model.py
import lnmt

# Initialize model with pre-trained weights
model = lnmt.Model('bert-base-uncased')

# Configure for classification
model.add_classification_head(num_classes=2)

# Set up training
trainer = lnmt.Trainer(
    model=model,
    learning_rate=2e-5,
    batch_size=16,
    max_epochs=3
)

# Train the model
trainer.fit(
    train_data='data/train.jsonl',
    validation_split=0.2,
    save_path='models/sentiment-classifier'
)

print("Training complete!")
```

```bash
python train_model.py
```

### Step 4: Test Your Model

```python
# test_model.py
import lnmt

# Load the trained model
model = lnmt.Model.load('models/sentiment-classifier')

# Make predictions
texts = [
    "I absolutely love this product!",
    "This is the worst thing ever.",
    "The weather is okay today."
]

for text in texts:
    prediction = model.predict(text)
    confidence = prediction['confidence']
    label = prediction['label']
    print(f"Text: {text}")
    print(f"Prediction: {label} (confidence: {confidence:.2f})")
    print("-" * 50)
```

```bash
python test_model.py
```

## 🎯 Common Use Cases

### Text Classification

```python
# Quick text classification setup
classifier = lnmt.TextClassifier()
classifier.train(
    texts=["happy text", "sad text"],
    labels=["positive", "negative"]
)

result = classifier.predict("I'm feeling great today!")
```

### Text Generation

```python
# Generate text with a pre-trained model
generator = lnmt.TextGenerator('gpt-2')
text = generator.generate(
    prompt="The future of AI is",
    max_length=100,
    temperature=0.7
)
print(text)
```

### Question Answering

```python
# Set up Q&A system
qa_model = lnmt.QuestionAnswering('bert-base-uncased')
answer = qa_model.answer(
    question="What is LNMT?",
    context="LNMT is a toolkit for large neural models..."
)
print(answer)
```

## 🔄 Using the CLI

LNMT provides powerful command-line tools:

```bash
# Check system status
lnmt status

# List available models
lnmt models list

# Download a pre-trained model
lnmt models download bert-base-uncased

# Start training with config file
lnmt train --config config.yaml

# Evaluate a model
lnmt evaluate --model models/my-model --data data/test.jsonl

# Deploy a model
lnmt deploy --model models/my-model --port 8080
```

## ⚙️ Configuration Files

Create a `config.yaml` for reproducible experiments:

```yaml
# config.yaml
model:
  name: "bert-base-uncased"
  task: "classification"
  num_classes: 2

training:
  learning_rate: 2e-5
  batch_size: 16
  max_epochs: 10
  early_stopping: true
  patience: 3

data:
  train_path: "data/train.jsonl"
  val_path: "data/val.jsonl"
  test_path: "data/test.jsonl"
  max_seq_length: 512

optimization:
  optimizer: "adamw"
  weight_decay: 0.01
  warmup_steps: 1000
  gradient_clipping: 1.0

logging:
  wandb: true
  project_name: "my-lnmt-project"
  log_every: 100
```

Run with configuration:

```bash
lnmt train --config config.yaml
```

## 🐛 Troubleshooting

### Common Issues

**Import Error**: `ModuleNotFoundError: No module named 'lnmt'`
```bash
# Ensure LNMT is installed
pip install lnmt

# Check Python path
python -c "import sys; print(sys.path)"
```

**CUDA Not Detected**: GPU training not working
```bash
# Check CUDA installation
nvidia-smi

# Install CUDA-compatible PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Out of Memory**: GPU memory issues
```python
# Reduce batch size
trainer = lnmt.Trainer(batch_size=8)  # Instead of 16

# Enable gradient accumulation
trainer = lnmt.Trainer(
    batch_size=8,
    accumulate_grad_batches=2  # Effective batch size = 16
)
```

### Getting Help

1. **Check Documentation**: [docs.lnmt.ai](https://docs.lnmt.ai)
2. **Search Issues**: [GitHub Issues](https://github.com/your-org/lnmt/issues)
3. **Ask Questions**: [GitHub Discussions](https://github.com/your-org/lnmt/discussions)
4. **Join Discord**: [Community Chat](https://discord.gg/lnmt)

## 📚 Next Steps

Now that you've completed the quick start:

1. **[📋 API Reference](api_reference.md)** - Explore all available methods and classes
2. **[🏗️ Architecture Guide](architecture.md)** - Understand LNMT's design
3. **[🎓 Tutorials](tutorials/)** - Learn advanced techniques
4. **[💼 Examples](../examples/)** - See real-world use cases
5. **[🛠️ Developer Guide](developer_guide.md)** - Contribute to LNMT

## 🎉 Success!

You've successfully:
- ✅ Installed LNMT
- ✅ Created your first project
- ✅ Trained a model
- ✅ Made predictions
- ✅ Learned CLI commands

**Ready for more?** Check out our [examples directory](../examples/) for production-ready code samples and advanced use cases.

---

**Questions?** Join our [Discord community](https://discord.gg/lnmt) or open an issue on [GitHub](https://github.com/your-org/lnmt/issues).