from ultralytics import YOLO
import os
from pathlib import Path

def get_base_dir():
    """Get base directory relative to this script's location."""
    return Path(__file__).resolve().parent.parent.parent

def main():
    base_dir = get_base_dir()
    model_dir = base_dir / "model" / "color_model"
    dataset_yaml = model_dir / "dataset.yaml"

    # Validate dataset exists
    if not dataset_yaml.exists():
        print(f"❌ Dataset config not found: {dataset_yaml}")
        print("   Run prepare_dataset.py first!")
        return

    # Check for training data
    train_images = model_dir / "train" / "images"
    if not train_images.exists() or len(list(train_images.glob("*"))) == 0:
        print(f"❌ No training images found in: {train_images}")
        print("   Run prepare_dataset.py first!")
        return

    print("=" * 60)
    print("🚀 YOLO MODEL TRAINING - OPTIMIZED FOR MANGA TEXT")
    print("=" * 60)
    print(f"📁 Base directory: {base_dir}")
    print(f"📁 Dataset config: {dataset_yaml}")
    print()

    # Model selection
    print("📦 Model Selection:")
    print("   1. YOLOv8n (nano) - RECOMMENDED for small text ⭐")
    print("   2. YOLOv8s (small)")
    print("   3. YOLOv8m (medium) - original (slower, heavier)")
    print("   4. YOLOv9c (medium) - Newest, best accuracy")
    print("   5. YOLOv10m (medium) - Latest version")
    
    model_choice = input("\nSelect model (1-5) [default: 1]: ").strip()
    
    model_map = {
        '1': 'yolov8n.pt',
        '2': 'yolov8s.pt',
        '3': 'yolov8m.pt',
        '4': 'yolov9c.pt',
        '5': 'yolov10m.pt'
    }
    
    selected_model = model_map.get(model_choice, 'yolov8n.pt')
    print(f"\n✅ Selected model: {selected_model}")

    print("\n📦 Loading model...")
    try:
        model = YOLO(selected_model)
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    # Training parameters
    print("\n⚙️ TRAINING PARAMETERS")
    print("=" * 60)
    
    epochs_input = input("Enter number of epochs [default: 150]: ").strip()
    epochs = int(epochs_input) if epochs_input.isdigit() else 150
    
    # 1024 to handle high-resolution manga pages natively
    img_size_input = input("Enter image size (640/1024) [default: 1024 - BEST for high-res manga]: ").strip()
    try:
        imgsz = int(img_size_input)
        if imgsz not in [640, 800, 1024, 1280]:
            imgsz = 1024
    except ValueError:
        imgsz = 1024
    
    # Default to 8 to account for the larger 1024 image size and prevent GPU OOM errors
    batch_size_input = input("Enter batch size [default: 8]: ").strip()
    batch_size = int(batch_size_input) if batch_size_input.isdigit() else 8
    
    print("\n✅ Training Configuration:")
    print(f"   📊 Epochs: {epochs}")
    print(f"   📐 Image size: {imgsz}x{imgsz}")
    print(f"   📦 Batch size: {batch_size}")
    print(f"   🎯 Early stopping patience: 30 epochs")
    print(f"   🔄 Save checkpoint every 10 epochs")
    print()

    # Create a dynamic run name based on the selected model to prevent overwriting
    run_name = f"train_{selected_model.replace('.pt', '')}"
    runs_dir = base_dir / "runs"

    # Train the model
    try:
        print("🏋️ Starting training...")
        print("(This may take a while depending on your system)")
        print()
        
        results = model.train(
            # Data
            data=str(dataset_yaml),
            
            # Training parameters
            epochs=epochs,
            imgsz=imgsz,  
            batch=batch_size,
            device=0,  # GPU 0
            
            # 🚀 Windows Speed & Stability Optimizations
            workers=4,         # Safe multiprocessing: feeds the GPU faster without crashing Windows
            amp=True,          # Automatic Mixed Precision: speeds up GPU calculations
            
            # Model saving - Dynamically separating runs
            project=str(runs_dir),
            name=run_name,
            exist_ok=False,  
            save=True,
            save_period=10,  
            
            # Early stopping
            
            patience=30,  
            
            # Augmentation
            hsv_h=0.015,  
            hsv_s=0.7,    
            hsv_v=0.4,    
            degrees=10,   
            translate=0.1,  
            scale=0.5,    
            flipud=0.5,   
            fliplr=0.5,   
            mosaic=1.0,   
            mixup=0.0,    
            
            # Optimizer
            optimizer='SGD',  
            lr0=0.01,     
            lrf=0.01,     
            
            # Loss function weights
            cls=0.5,      
            box=7.5,      
            dfl=1.5,      
            
            # Other
            close_mosaic=10,  
            plots=True,       
            verbose=True,     
        )

        print("\n" + "=" * 60)
        print("✅ Training complete!")
        print(f"📁 Results saved to: {results.save_dir}")
        print(f"📦 Best model: {os.path.join(results.save_dir, 'weights', 'best.pt')}")
        print()
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return

if __name__ == "__main__":
    main()