# 📋 LNMT API Reference

Complete reference for all LNMT classes, methods, and functions.

## Table of Contents

- [Core Classes](#core-classes)
- [Model Management](#model-management)
- [Training & Optimization](#training--optimization)
- [Data Handling](#data-handling)
- [Deployment & Serving](#deployment--serving)
- [Utilities](#utilities)
- [Configuration](#configuration)
- [Examples](#examples)

---

## Core Classes

### `lnmt.Model`

The main model class for creating, training, and using neural models.

```python
class Model:
    def __init__(
        self,
        model_name: str = None,
        config: Dict = None,
        pretrained: bool = True,
        cache_dir: str = None
    )
```

**Parameters:**
- `model_name` (str): Name of the pre-trained model or architecture
- `config` (Dict): Model configuration dictionary
- `pretrained` (bool): Whether to load pre-trained weights
- `cache_dir` (str): Directory to cache downloaded models

**Methods:**

#### `train()`
```python
def train(
    self,
    data_path: str,
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    validation_split: float = 0.1,
    save_path: str = None,
    **kwargs
) -> Dict[str, Any]
```

Train the model on provided data.

**Returns:** Training metrics and history

#### `predict()`
```python
def predict(
    self,
    inputs: Union[str, List[str], torch.Tensor],
    batch_size: int = 32,
    return_probabilities: bool = False
) -> Union[Dict, List[Dict]]
```

Make predictions on input data.

**Returns:** Predictions with labels, scores, and optional probabilities

#### `save()`
```python
def save(
    self,
    path: str,
    include_optimizer: bool = False,
    include_scheduler: bool = False
) -> None
```

Save model to disk.

#### `load()`
```python
@classmethod
def load(
    cls,
    path: str,
    map_location: str = None,
    strict: bool = True
) -> 'Model'
```

Load model from disk.

**Example:**
```python
# Create and train a model
model = lnmt.Model('bert-base-uncased')
model.add_classification_head(num_classes=3)
metrics = model.train(
    data_path='data/train.jsonl',
    epochs=5,
    batch_size=16
)

# Make predictions
predictions = model.predict(["This is a test sentence."])
print(predictions)

# Save model
model.save('models/my-classifier')

# Load model later
loaded_model = lnmt.Model.load('models/my-classifier')
```

---

## Model Management

### `lnmt.ModelHub`

Manage model downloads, versions, and metadata.

```python
class ModelHub:
    def __init__(self, cache_dir: str = None)
```

**Methods:**

#### `list_models()`
```python
def list_models(
    self,
    task: str = None,
    language: str = None,
    sort_by: str = 'downloads'
) -> List[Dict]
```

List available models.

#### `download()`
```python
def download(
    self,
    model_name: str,
    force: bool = False,
    progress: bool = True
) -> str
```

Download a model to local cache.

#### `info()`
```python
def info(self, model_name: str) -> Dict
```

Get detailed information about a model.

**Example:**
```python
hub = lnmt.ModelHub()

# List all text classification models
models = hub.list_models(task='text-classification')

# Download a specific model
path = hub.download('distilbert-base-uncased')

# Get model information
info = hub.info('bert-large-uncased')
print(f"Model size: {info['size']}")
print(f"Languages: {info['languages']}")
```

---

## Training & Optimization

### `lnmt.Trainer`

Advanced training with monitoring, checkpointing, and optimization.

```python
class Trainer:
    def __init__(
        self,
        model: Model,
        optimizer: str = 'adamw',
        learning_rate: float = 1e-4,
        weight_decay: float = 0.01,
        warmup_steps: int = 1000,
        max_grad_norm: float = 1.0,
        device: str = 'auto'
    )
```

**Methods:**

#### `fit()`
```python
def fit(
    self,
    train_data: Union[str, Dataset],
    val_data: Union[str, Dataset] = None,
    max_epochs: int = 10,
    patience: int = 3,
    min_delta: float = 1e-4,
    save_best: bool = True,
    checkpoint_dir: str = None,
    callbacks: List = None
) -> Dict
```

Train model with advanced features.

#### `evaluate()`
```python
def evaluate(
    self,
    data: Union[str, Dataset],
    batch_size: int = 32,
    metrics: List[str] = None
) -> Dict
```

Evaluate model performance.

#### `predict()`
```python
def predict(
    self,
    data: Union[str, Dataset],
    batch_size: int = 32,
    output_file: str = None
) -> List[Dict]
```

Generate predictions on dataset.

**Example:**
```python
model = lnmt.Model('roberta-base')
trainer = lnmt.Trainer(
    model=model,
    learning_rate=2e-5,
    warmup_steps=500
)

# Train with validation and early stopping
results = trainer.fit(
    train_data='data/train.jsonl',
    val_data='data/val.jsonl',
    max_epochs=20,
    patience=3,
    save_best=True
)

print(f"Best validation score: {results['best_score']}")
```

### `lnmt.DistributedTrainer`

Multi-GPU and multi-node training.

```python
class DistributedTrainer(Trainer):
    def __init__(
        self,
        model: Model,
        gpus: List[int] = None,
        nodes: int = 1,
        strategy: str = 'ddp',
        precision: str = 'fp16',
        **kwargs
    )
```

**Example:**
```python
# Multi-GPU training
trainer = lnmt.DistributedTrainer(
    model=model,
    gpus=[0, 1, 2, 3],
    strategy='ddp',
    precision='fp16'
)

trainer.fit(train_data='large_dataset.jsonl')
```

---

## Data Handling

### `lnmt.Dataset`

Base dataset class for handling various data formats.

```python
class Dataset:
    def __init__(
        self,
        data: Union[str, List, Dict],
        tokenizer: Tokenizer = None,
        max_length: int = 512,
        padding: bool = True,
        truncation: bool = True
    )
```

**Methods:**

#### `from_jsonl()`
```python
@classmethod
def from_jsonl(
    cls,
    file_path: str,
    text_column: str = 'text',
    label_column: str = 'label',
    **kwargs
) -> 'Dataset'
```

Create dataset from JSONL file.

#### `from_csv()`
```python
@classmethod
def from_csv(
    cls,
    file_path: str,
    text_column: str = 'text',
    label_column: str = 'label',
    **kwargs
) -> 'Dataset'
```

Create dataset from CSV file.

#### `split()`
```python
def split(
    self,
    train_size: float = 0.8,
    val_size: float = 0.1,
    test_size: float = 0.1,
    random_state: int = 42
) -> Tuple['Dataset', 'Dataset', 'Dataset']
```

Split dataset into train/validation/test sets.

**Example:**
```python
# Load from JSONL
dataset = lnmt.Dataset.from_jsonl(
    'data/reviews.jsonl',
    text_column='review_text',
    label_column='sentiment'
)

# Split data
train_data, val_data, test_data = dataset.split(
    train_size=0.7,
    val_size=0.15,
    test_size=0.15
)

print(f"Train size: {len(train_data)}")
print(f"Validation size: {len(val_data)}")
print(f"Test size: {len(test_data)}")
```

### `lnmt.DataLoader`

Efficient data loading with batching and preprocessing.

```python
class DataLoader:
    def __init__(
        self,
        dataset: Dataset,
        batch_size: int = 32,
        shuffle: bool = False,
        num_workers: int = 0,
        pin_memory: bool = False
    )
```

---

## Deployment & Serving

### `lnmt.Deployment`

Deploy models for production inference.

```python
class Deployment:
    def __init__(
        self,
        model: Union[str, Model],
        name: str = None,
        replicas: int = 1,
        auto_scaling: bool = False,
        max_replicas: int = 10,
        cpu_request: str = '100m',
        memory_request: str = '512Mi',
        gpu_request: int = 0
    )
```

**Methods:**

#### `deploy()`
```python
def deploy(
    self,
    platform: str = 'kubernetes',
    namespace: str = 'default',
    port: int = 8080,
    health_check: bool = True,
    monitoring: bool = True
) -> Dict
```

Deploy model to specified platform.

#### `update()`
```python
def update(
    self,
    model_version: str = None,
    replicas: int = None,
    rolling_update: bool = True
) -> Dict
```

Update existing deployment.

#### `scale()`
```python
def scale(self, replicas: int) -> Dict
```

Scale deployment to specified number of replicas.

#### `delete()`
```python
def delete(self) -> bool
```

Delete the deployment.

**Example:**
```python
# Deploy model to Kubernetes
deployment = lnmt.Deployment(
    model='models/sentiment-classifier',
    name='sentiment-api',
    replicas=3,
    auto_scaling=True
)

# Deploy with monitoring
result = deployment.deploy(
    platform='kubernetes',
    port=8080,
    monitoring=True
)

print(f"Deployment URL: {result['url']}")

# Update to new model version
deployment.update(model_version='v2.0')
```

### `lnmt.InferenceServer`

Local inference server for development and testing.

```python
class InferenceServer:
    def __init__(
        self,
        model: Union[str, Model],
        host: str = '0.0.0.0',
        port: int = 8080,
        workers: int = 1,
        timeout: int = 30
    )
```

**Methods:**

#### `start()`
```python
def start(self, background: bool = False) -> None
```

Start the inference server.

#### `stop()`
```python
def stop(self) -> None
```

Stop the inference server.

**Example:**
```python
# Start local inference server
server = lnmt.InferenceServer(
    model='models/my-model',
    port=8080,
    workers=4
)

server.start()
# Server available at http://localhost:8080/predict
```

---

## Utilities

### `lnmt.metrics`

Evaluation metrics for different tasks.

#### Classification Metrics

```python
def accuracy_score(y_true: List, y_pred: List) -> float
def precision_score(y_true: List, y_pred: List, average: str = 'macro') -> float
def recall_score(y_true: List, y_pred: List, average: str = 'macro') -> float
def f1_score(y_true: List, y_pred: List, average: str = 'macro') -> float
def classification_report(y_true: List, y_pred: List) -> Dict
```

#### Regression Metrics

```python
def mean_squared_error(y_true: List, y_pred: List) -> float
def mean_absolute_error(y_true: List, y_pred: List) -> float
def r2_score(y_true: List, y_pred: List) -> float
```

#### Generation Metrics

```python
def bleu_score(references: List[str], candidates: List[str]) -> float
def rouge_score(references: List[str], candidates: List[str]) -> Dict
```

**Example:**
```python
from lnmt.metrics import accuracy_score, classification_report

y_true = ['positive', 'negative', 'positive', 'neutral']
y_pred = ['positive', 'negative', 'neutral', 'neutral']

acc = accuracy_score(y_true, y_pred)
report = classification_report(y_true, y_pred)

print(f"Accuracy: {acc:.3f}")
print(report)
```

### `lnmt.utils`

General utility functions.

#### `lnmt.utils.gpu`

GPU utilities and device management.

```python
def is_available() -> bool
def device_count() -> int
def get_device(device_id: int = None) -> torch.device
def memory_info(device_id: int = 0) -> Dict
def clear_cache() -> None
```

#### `lnmt.utils.logging`

Logging configuration and utilities.

```python
def setup_logging(
    level: str = 'INFO',
    format: str = None,
    file: str = None
) -> None

def get_logger(name: str) -> logging.Logger
```

#### `lnmt.utils.checkpoint`

Model checkpointing utilities.

```python
def save_checkpoint(
    model: Model,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    loss: float,
    path: str,
    metadata: Dict = None
) -> None

def load_checkpoint(
    path: str,
    model: Model = None,
    optimizer: torch.optim.Optimizer = None
) -> Dict
```

**Example:**
```python
from lnmt.utils import gpu, logging

# Check GPU availability
if gpu.is_available():
    print(f"GPUs available: {gpu.device_count()}")
    device = gpu.get_device(0)
    memory = gpu.memory_info(0)
    print(f"GPU memory: {memory['used']}/{memory['total']} MB")

# Setup logging
logging.setup_logging(level='DEBUG', file='training.log')
logger = logging.get_logger(__name__)
logger.info("Training started")
```

---

## Configuration

### `lnmt.Config`

Configuration management for reproducible experiments.

```python
class Config:
    def __init__(
        self,
        config_file: str = None,
        **kwargs
    )
```

**Methods:**

#### `from_yaml()`
```python
@classmethod
def from_yaml(cls, file_path: str) -> 'Config'
```

Load configuration from YAML file.

#### `from_dict()`
```python
@classmethod
def from_dict(cls, config_dict: Dict) -> 'Config'
```

Create configuration from dictionary.

#### `save()`
```python
def save(self, file_path: str) -> None
```

Save configuration to file.

#### `update()`
```python
def update(self, **kwargs) -> None
```

Update configuration parameters.

**Example:**
```python
# Create configuration
config = lnmt.Config(
    model_name='bert-base-uncased',
    learning_rate=2e-5,
    batch_size=16,
    max_epochs=10
)

# Save to file
config.save('config.yaml')

# Load from file
config = lnmt.Config.from_yaml('config.yaml')

# Update parameters
config.update(learning_rate=1e-5, batch_size=32)
```

### Configuration Schema

Standard configuration structure:

```yaml
# Full configuration example
model:
  name: "bert-base-uncased"
  architecture: "transformer"
  hidden_size: 768
  num_layers: 12
  num_attention_heads: 12
  intermediate_size: 3072
  dropout: 0.1
  task: "classification"
  num_classes: 3

training:
  optimizer: "adamw"
  learning_rate: 2e-5
  weight_decay: 0.01
  warmup_steps: 1000
  max_grad_norm: 1.0
  batch_size: 16
  max_epochs: 20
  early_stopping: true
  patience: 3
  min_delta: 1e-4
  gradient_accumulation_steps: 1
  precision: "fp16"

data:
  train_path: "data/train.jsonl"
  val_path: "data/val.jsonl"
  test_path: "data/test.jsonl"
  text_column: "text"
  label_column: "label"
  max_seq_length: 512
  padding: true
  truncation: true
  validation_split: 0.1

environment:
  device: "auto"
  num_workers: 4
  pin_memory: true
  distributed: false
  mixed_precision: true
  compile: false

logging:
  level: "INFO"
  wandb: true
  project_name: "lnmt-experiments"
  run_name: null
  log_every: 100
  save_every: 1000

checkpointing:
  save_dir: "checkpoints"
  save_best: true
  save_last: true
  monitor: "val_loss"
  mode: "min"
```

---

## Examples

### Complete Training Pipeline

```python
import lnmt
from lnmt.metrics import classification_report

# Load configuration
config = lnmt.Config.from_yaml('config.yaml')

# Setup logging
lnmt.utils.logging.setup_logging(level=config.logging.level)
logger = lnmt.utils.logging.get_logger(__name__)

# Create model
model = lnmt.Model(
    model_name=config.model.name,
    task=config.model.task,
    num_classes=config.model.num_classes
)

# Setup trainer
trainer = lnmt.Trainer(
    model=model,
    optimizer=config.training.optimizer,
    learning_rate=config.training.learning_rate,
    weight_decay=config.training.weight_decay,
    warmup_steps=config.training.warmup_steps
)

# Load data
train_data = lnmt.Dataset.from_jsonl(
    config.data.train_path,
    text_column=config.data.text_column,
    label_column=config.data.label_column,
    max_length=config.data.max_seq_length
)

val_data = lnmt.Dataset.from_jsonl(
    config.data.val_path,
    text_column=config.data.text_column,
    label_column=config.data.label_column,
    max_length=config.data.max_seq_length
)

# Train model
logger.info("Starting training...")
results = trainer.fit(
    train_data=train_data,
    val_data=val_data,
    max_epochs=config.training.max_epochs,
    patience=config.training.patience,
    save_best=True
)

# Evaluate model
test_data = lnmt.Dataset.from_jsonl(config.data.test_path)
test_results = trainer.evaluate(test_data)

logger.info(f"Test accuracy: {test_results['accuracy']:.3f}")
logger.info(f"Test F1: {test_results['f1']:.3f}")

# Save final model
model.save('models/final-model')
logger.info("Training completed successfully!")
```

### Production Deployment

```python
import lnmt

# Load trained model
model = lnmt.Model.load('models/sentiment-classifier')

# Create deployment configuration
deployment = lnmt.Deployment(
    model=model,
    name='sentiment-api-v1',
    replicas=3,
    auto_scaling=True,
    max_replicas=10,
    cpu_request='500m',
    memory_request='1Gi',
    gpu_request=0
)

# Deploy to Kubernetes
result = deployment.deploy(
    platform='kubernetes',
    namespace='ml-services',
    port=8080,
    health_check=True,
    monitoring=True
)

print(f"Deployment successful!")
print(f"Service URL: {result['service_url']}")
print(f"Health check: {result['health_endpoint']}")
print(f"Metrics: {result['metrics_endpoint']}")

# Test the deployment
import requests

response = requests.post(
    f"{result['service_url']}/predict",
    json={"text": "I love this product!"}
)

prediction = response.json()
print(f"Prediction: {prediction}")
```

### Batch Processing

```python
import lnmt
from tqdm import tqdm

# Load model
model = lnmt.Model.load('models/text-classifier')

# Process large dataset in batches
def process_batch_file(input_file: str, output_file: str, batch_size: int = 1000):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        batch = []
        
        for line in tqdm(infile, desc="Processing"):
            batch.append(line.strip())
            
            if len(batch) >= batch_size:
                # Process batch
                predictions = model.predict(batch, batch_size=batch_size)
                
                # Write results
                for text, pred in zip(batch, predictions):
                    result = {
                        'text': text,
                        'prediction': pred['label'],
                        'confidence': pred['confidence']
                    }
                    outfile.write(json.dumps(result) + '\n')
                
                batch = []
        
        # Process remaining items
        if batch:
            predictions = model.predict(batch)
            for text, pred in zip(batch, predictions):
                result = {
                    'text': text,
                    'prediction': pred['label'],
                    'confidence': pred['confidence']
                }
                outfile.write(json.dumps(result) + '\n')

# Process large file
process_batch_file('large_dataset.txt', 'predictions.jsonl')
```

### Custom Model Architecture

```python
import lnmt
import torch.nn as nn

# Define custom model
class CustomClassifier(lnmt.Model):
    def __init__(self, vocab_size: int, embed_dim: int, num_classes: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(embed_dim, 128, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(0.3)
        self.classifier = nn.Linear(256, num_classes)
    
    def forward(self, input_ids, attention_mask=None):
        embedded = self.embedding(input_ids)
        lstm_out, _ = self.lstm(embedded)
        
        # Use last hidden state
        if attention_mask is not None:
            # Get last non-padded token
            lengths = attention_mask.sum(dim=1) - 1
            last_hidden = lstm_out[range(len(lengths)), lengths]
        else:
            last_hidden = lstm_out[:, -1]
        
        dropped = self.dropout(last_hidden)
        logits = self.classifier(dropped)
        return {'logits': logits}

# Create and train custom model
model = CustomClassifier(vocab_size=30000, embed_dim=300, num_classes=3)
trainer = lnmt.Trainer(model, learning_rate=1e-3)

# Train as usual
results = trainer.fit(
    train_data='data/train.jsonl',
    val_data='data/val.jsonl',
    max_epochs=10
)
```

---

## Error Handling

LNMT provides structured error handling:

```python
from lnmt.exceptions import (
    LNMTError,
    ModelNotFoundError,
    TrainingError,
    InferenceError,
    ConfigurationError
)

try:
    model = lnmt.Model('non-existent-model')
except ModelNotFoundError as e:
    print(f"Model not found: {e}")

try:
    trainer.fit(train_data='invalid_path.jsonl')
except TrainingError as e:
    print(f"Training failed: {e}")
    print(f"Suggested fix: {e.suggestion}")
```

---

## Performance Tips

1. **Use Mixed Precision Training**:
```python
trainer = lnmt.Trainer(model, precision='fp16')
```

2. **Gradient Accumulation for Large Batches**:
```python
trainer = lnmt.Trainer(
    model,
    batch_size=8,
    accumulate_grad_batches=4  # Effective batch size: 32
)
```

3. **Efficient Data Loading**:
```python
dataloader = lnmt.DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,
    pin_memory=True
)
```

4. **Model Compilation** (PyTorch 2.0+):
```python
model = lnmt.Model('bert-base-uncased')
model.compile()  # Faster inference
```

---

## Version Compatibility

| LNMT Version | Python | PyTorch | Transformers |
|--------------|--------|---------|--------------|
| 1.0.x        | 3.8+   | 1.12+   | 4.20+        |
| 1.1.x        | 3.8+   | 1.13+   | 4.25+        |
| 1.2.x        | 3.9+   | 2.0+    | 4.30+        |

---

**Need help?** Check our [troubleshooting guide](troubleshooting.md) or join our [Discord community](https://discord.gg/lnmt).