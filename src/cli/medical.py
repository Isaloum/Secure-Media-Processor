"""Medical imaging CLI commands."""

import click
from colorama import Fore, Style
from pathlib import Path
from typing import Optional
import numpy as np


@click.group()
def medical():
    """Medical imaging tools for DICOM processing and analysis."""
    pass


@medical.command('dicom-info')
@click.argument('path', type=click.Path(exists=True))
@click.option('--series', is_flag=True, help='List all series in directory')
def dicom_info(path: str, series: bool):
    """Display DICOM file or series information."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Reading DICOM data...{Style.RESET_ALL}\n")

    try:
        processor = DICOMProcessor()
        path_obj = Path(path)

        if series or path_obj.is_dir():
            # List all series
            series_list = processor.get_series_list(path)

            if not series_list:
                click.echo(f"{Fore.YELLOW}No DICOM series found in directory{Style.RESET_ALL}")
                return

            click.echo(f"{Fore.GREEN}Found {len(series_list)} series:{Style.RESET_ALL}\n")

            for i, s in enumerate(series_list, 1):
                click.echo(f"{Fore.YELLOW}Series {i}:{Style.RESET_ALL}")
                click.echo(f"  UID: {s['series_uid'][:50]}...")
                click.echo(f"  Modality: {s['modality']}")
                click.echo(f"  Description: {s['series_description'] or 'N/A'}")
                click.echo(f"  Patient ID: {s['patient_id']}")
                click.echo(f"  Study Date: {s['study_date']}")
                click.echo(f"  Slices: {s['num_slices']}")
                click.echo()
        else:
            # Single file info
            pixel_array, metadata = processor.read_dicom(path)

            click.echo(f"{Fore.GREEN}DICOM File Information{Style.RESET_ALL}\n")

            click.echo(f"{Fore.YELLOW}Patient:{Style.RESET_ALL}")
            click.echo(f"  ID: {metadata.patient_id or 'N/A'}")
            click.echo(f"  Name: {metadata.patient_name or 'N/A'}")
            click.echo(f"  Sex: {metadata.patient_sex or 'N/A'}")
            click.echo(f"  Age: {metadata.patient_age or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Study:{Style.RESET_ALL}")
            click.echo(f"  Date: {metadata.study_date or 'N/A'}")
            click.echo(f"  Description: {metadata.study_description or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Series:{Style.RESET_ALL}")
            click.echo(f"  Modality: {metadata.modality or 'N/A'}")
            click.echo(f"  Description: {metadata.series_description or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Image:{Style.RESET_ALL}")
            click.echo(f"  Dimensions: {metadata.rows} x {metadata.columns}")
            click.echo(f"  Pixel Spacing: {metadata.pixel_spacing or 'N/A'}")
            click.echo(f"  Slice Thickness: {metadata.slice_thickness or 'N/A'}")

            if metadata.modality == 'MR':
                click.echo(f"\n{Fore.YELLOW}MRI Parameters:{Style.RESET_ALL}")
                click.echo(f"  Field Strength: {metadata.magnetic_field_strength or 'N/A'} T")
                click.echo(f"  Echo Time (TE): {metadata.echo_time or 'N/A'} ms")
                click.echo(f"  Repetition Time (TR): {metadata.repetition_time or 'N/A'} ms")
                click.echo(f"  Flip Angle: {metadata.flip_angle or 'N/A'} degrees")

    except Exception as e:
        click.echo(f"{Fore.RED}Error reading DICOM: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('anonymize')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--keep-uids', is_flag=True, help='Keep original study/series UIDs')
def anonymize_dicom(input_path: str, output_path: str, keep_uids: bool):
    """Anonymize DICOM file for HIPAA compliance."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Anonymizing DICOM file...{Style.RESET_ALL}")

    try:
        processor = DICOMProcessor()
        result = processor.anonymize_dicom(input_path, output_path, keep_study_uid=keep_uids)

        click.echo(f"{Fore.GREEN}File anonymized successfully!{Style.RESET_ALL}")
        click.echo(f"  Output: {result['output']}")
        click.echo(f"  New Patient ID: {result['new_patient_id']}")
        click.echo(f"  Fields removed: {len(result['removed_fields'])}")

        if result['removed_fields']:
            click.echo(f"\n{Fore.YELLOW}Removed/anonymized fields:{Style.RESET_ALL}")
            for field in result['removed_fields'][:10]:
                click.echo(f"    - {field}")
            if len(result['removed_fields']) > 10:
                click.echo(f"    ... and {len(result['removed_fields']) - 10} more")

    except Exception as e:
        click.echo(f"{Fore.RED}Anonymization failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('convert')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--format', 'output_format', type=click.Choice(['png', 'nifti']),
              default='png', help='Output format')
@click.option('--window-center', type=float, help='Window center for contrast')
@click.option('--window-width', type=float, help='Window width for contrast')
def convert_dicom(input_path: str, output_path: str, output_format: str,
                  window_center: Optional[float], window_width: Optional[float]):
    """Convert DICOM to PNG or NIfTI format."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Converting DICOM to {output_format.upper()}...{Style.RESET_ALL}")

    try:
        processor = DICOMProcessor()

        if output_format == 'png':
            result = processor.convert_to_png(
                input_path, output_path,
                window_center=window_center,
                window_width=window_width
            )
            click.echo(f"{Fore.GREEN}Converted to PNG successfully!{Style.RESET_ALL}")
            click.echo(f"  Output: {result['output']}")
            click.echo(f"  Size: {result['size']}")
            click.echo(f"  Modality: {result['modality']}")

        elif output_format == 'nifti':
            result = processor.convert_to_nifti(input_path, output_path)
            click.echo(f"{Fore.GREEN}Converted to NIfTI successfully!{Style.RESET_ALL}")
            click.echo(f"  Output: {result['output']}")
            click.echo(f"  Volume shape: {result['volume_shape']}")
            click.echo(f"  Voxel spacing: {result['voxel_spacing']}")
            click.echo(f"  Slices: {result['num_slices']}")

    except Exception as e:
        click.echo(f"{Fore.RED}Conversion failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('preprocess')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--bias-correction/--no-bias-correction', default=True,
              help='Apply N4 bias field correction')
@click.option('--denoise/--no-denoise', default=True, help='Apply noise reduction')
@click.option('--normalize', type=click.Choice(['zscore', 'minmax', 'percentile']),
              default='zscore', help='Normalization method')
@click.option('--enhance-contrast', is_flag=True, help='Apply CLAHE contrast enhancement')
def preprocess_medical(input_path: str, output_path: str, bias_correction: bool,
                       denoise: bool, normalize: str, enhance_contrast: bool):
    """Preprocess medical image for ML analysis."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available
    from src.medical_preprocessing import (
        MedicalImagePreprocessor, PreprocessingConfig, NormalizationMethod
    )

    click.echo(f"{Fore.CYAN}Preprocessing medical image...{Style.RESET_ALL}")

    try:
        # Load image (DICOM or standard format)
        input_path_obj = Path(input_path)

        if input_path_obj.suffix.lower() in ['.dcm', '.dicom'] or input_path_obj.is_dir():
            if not check_dicom_available():
                click.echo(f"{Fore.RED}DICOM support not available{Style.RESET_ALL}")
                raise click.Abort()

            processor = DICOMProcessor()
            if input_path_obj.is_dir():
                volume = processor.read_dicom_series(input_path)
                image = volume.pixel_data
            else:
                image, _ = processor.read_dicom(input_path)
        else:
            from PIL import Image
            img = Image.open(input_path).convert('L')
            image = np.array(img, dtype=np.float32)

        # Configure preprocessing
        norm_method = {
            'zscore': NormalizationMethod.ZSCORE,
            'minmax': NormalizationMethod.MINMAX,
            'percentile': NormalizationMethod.PERCENTILE
        }[normalize]

        config = PreprocessingConfig(
            normalize=True,
            normalization_method=norm_method,
            denoise=denoise,
            bias_correction=bias_correction,
            enhance_contrast=enhance_contrast
        )

        # Run preprocessing
        preprocessor = MedicalImagePreprocessor(config)
        result = preprocessor.preprocess(image)

        # Save result
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if output_path_obj.suffix.lower() == '.npy':
            np.save(output_path, result.data)
        else:
            from PIL import Image
            # Normalize to 0-255 for saving as image
            img_data = result.data
            if img_data.ndim == 3:
                img_data = img_data[img_data.shape[0] // 2]  # Middle slice
            img_data = ((img_data - img_data.min()) / (img_data.max() - img_data.min() + 1e-8) * 255).astype(np.uint8)
            Image.fromarray(img_data).save(output_path)

        click.echo(f"{Fore.GREEN}Preprocessing complete!{Style.RESET_ALL}")
        click.echo(f"  Output: {output_path}")
        click.echo(f"  Original shape: {result.original_shape}")
        click.echo(f"  Final shape: {result.final_shape}")
        click.echo(f"\n{Fore.YELLOW}Steps applied:{Style.RESET_ALL}")
        for step in result.steps_applied:
            click.echo(f"    - {step}")

    except Exception as e:
        click.echo(f"{Fore.RED}Preprocessing failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('predict')
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--model', type=click.Path(exists=True), required=True,
              help='Path to trained model (.pt, .pth, or .onnx)')
@click.option('--model-type', type=click.Choice(['pytorch', 'onnx', 'torchscript']),
              default='pytorch', help='Model type')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU for inference')
@click.option('--generate-heatmap', is_flag=True, help='Generate attention heatmap')
@click.option('--output-report', type=click.Path(), help='Save report to file')
def predict_cancer(input_path: str, model: str, model_type: str, gpu: bool,
                   generate_heatmap: bool, output_report: Optional[str]):
    """Run cancer prediction on MRI image/volume."""
    from src.ml_inference import (
        CancerPredictionPipeline, ModelConfig, ModelType, PredictionType, check_ml_available
    )

    # Check ML availability
    ml_status = check_ml_available()
    if model_type in ['pytorch', 'torchscript'] and not ml_status['pytorch']:
        click.echo(f"{Fore.RED}PyTorch not available. Install with: pip install torch{Style.RESET_ALL}")
        raise click.Abort()
    if model_type == 'onnx' and not ml_status['onnx']:
        click.echo(f"{Fore.RED}ONNX Runtime not available. Install with: pip install onnxruntime{Style.RESET_ALL}")
        raise click.Abort()

    if gpu and not ml_status['gpu']:
        click.echo(f"{Fore.YELLOW}GPU not available, using CPU{Style.RESET_ALL}")
        gpu = False

    click.echo(f"{Fore.CYAN}Running cancer prediction...{Style.RESET_ALL}\n")

    try:
        # Configure model
        type_map = {
            'pytorch': ModelType.PYTORCH,
            'onnx': ModelType.ONNX,
            'torchscript': ModelType.TORCHSCRIPT
        }

        config = ModelConfig(
            model_path=model,
            model_type=type_map[model_type],
            prediction_type=PredictionType.BINARY,
            use_gpu=gpu,
            class_names=["No Cancer", "Cancer"]
        )

        # Create pipeline
        pipeline = CancerPredictionPipeline(config, use_preprocessing=True)

        # Check if DICOM
        input_path_obj = Path(input_path)
        if input_path_obj.suffix.lower() in ['.dcm', '.dicom'] or input_path_obj.is_dir():
            result = pipeline.predict_from_dicom(input_path, generate_report=True)
        else:
            # Load as numpy/image
            from PIL import Image
            img = Image.open(input_path).convert('L')
            image = np.array(img, dtype=np.float32)
            result = pipeline.predict_single(image, generate_heatmap=generate_heatmap)

        # Display results
        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}PREDICTION RESULTS{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}\n")

        if 'final_probability' in result:
            prob = result['final_probability']
            label = result['predicted_label']
            conf = result.get('confidence', prob if prob > 0.5 else 1 - prob)

            color = Fore.RED if label == 'Cancer' else Fore.GREEN
            click.echo(f"{Fore.YELLOW}Prediction:{Style.RESET_ALL} {color}{label}{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Cancer Probability:{Style.RESET_ALL} {prob * 100:.1f}%")
            click.echo(f"{Fore.YELLOW}Confidence:{Style.RESET_ALL} {conf * 100:.1f}%")

            if 'most_suspicious_slice' in result:
                click.echo(f"{Fore.YELLOW}Most Suspicious Slice:{Style.RESET_ALL} #{result['most_suspicious_slice'] + 1}")
                click.echo(f"{Fore.YELLOW}Total Slices:{Style.RESET_ALL} {result['num_slices']}")
        else:
            pred = result.get('prediction', {})
            click.echo(f"{Fore.YELLOW}Prediction:{Style.RESET_ALL} {pred.get('predicted_label', 'N/A')}")
            click.echo(f"{Fore.YELLOW}Confidence:{Style.RESET_ALL} {pred.get('confidence', 0) * 100:.1f}%")

        # Save report if requested
        if output_report and 'report' in result:
            Path(output_report).write_text(result['report'])
            click.echo(f"\n{Fore.GREEN}Report saved to: {output_report}{Style.RESET_ALL}")

        # Print full report to console
        if 'report' in result:
            click.echo(f"\n{result['report']}")

    except Exception as e:
        click.echo(f"{Fore.RED}Prediction failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('segment')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--model', type=click.Path(exists=True), help='Path to trained U-Net model (.pt or .pth)')
@click.option('--variant', type=click.Choice(['standard', 'attention', 'residual']),
              default='standard', help='U-Net architecture variant')
@click.option('--threshold', type=float, default=0.5, help='Binary mask threshold (0-1)')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU for inference')
@click.option('--save-probability', is_flag=True, help='Save probability map alongside mask')
@click.option('--output-format', type=click.Choice(['png', 'npy', 'both']),
              default='png', help='Output format for segmentation mask')
def segment_image(input_path: str, output_path: str, model: Optional[str], variant: str,
                  threshold: float, gpu: bool, save_probability: bool, output_format: str):
    """Run U-Net segmentation on medical image for tumor/lesion detection."""
    from src.unet_segmentation import (
        UNetSegmentation, SegmentationConfig, UNetVariant, check_segmentation_available
    )

    # Check dependencies
    seg_status = check_segmentation_available()
    if not seg_status['pytorch']:
        click.echo(f"{Fore.RED}PyTorch not available. Install with: pip install torch{Style.RESET_ALL}")
        raise click.Abort()

    if gpu and not seg_status['gpu']:
        click.echo(f"{Fore.YELLOW}GPU not available, using CPU{Style.RESET_ALL}")
        gpu = False

    click.echo(f"{Fore.CYAN}Running U-Net segmentation...{Style.RESET_ALL}\n")

    try:
        # Configure segmentation
        variant_map = {
            'standard': UNetVariant.STANDARD,
            'attention': UNetVariant.ATTENTION,
            'residual': UNetVariant.RESIDUAL
        }

        config = SegmentationConfig(
            variant=variant_map[variant],
            use_gpu=gpu,
            threshold=threshold,
            apply_post_processing=True
        )

        # Create pipeline
        pipeline = UNetSegmentation(config)

        # Load model if provided
        if model:
            pipeline.load_model(model)
            click.echo(f"{Fore.GREEN}Loaded model:{Style.RESET_ALL} {model}")
        else:
            pipeline.create_model()
            click.echo(f"{Fore.YELLOW}Using untrained model (demo mode){Style.RESET_ALL}")

        # Load input image
        input_path_obj = Path(input_path)

        if input_path_obj.suffix.lower() in ['.dcm', '.dicom'] or input_path_obj.is_dir():
            from src.dicom_processor import DICOMProcessor, check_dicom_available
            if not check_dicom_available():
                click.echo(f"{Fore.RED}DICOM support not available{Style.RESET_ALL}")
                raise click.Abort()

            result_dict = pipeline.segment_from_dicom(input_path, preprocess=True)

            if 'results' in result_dict:
                # Volume segmentation
                results = result_dict['results']
                click.echo(f"\n{Fore.GREEN}Volume Segmentation Complete{Style.RESET_ALL}")
                click.echo(f"  Slices processed: {result_dict['num_slices']}")
                click.echo(f"  Total segmented pixels: {result_dict['total_volume_pixels']:,}")
                click.echo(f"  Slice with max area: #{result_dict['max_area_slice'] + 1}")

                # Save volume mask
                volume_mask = np.stack([r.mask for r in results], axis=0)
                output_path_obj = Path(output_path)

                if output_format in ['npy', 'both']:
                    npy_path = output_path_obj.with_suffix('.npy')
                    np.save(npy_path, volume_mask)
                    click.echo(f"  Mask saved: {npy_path}")

                if output_format in ['png', 'both']:
                    # Save middle slice as PNG
                    from PIL import Image
                    mid_idx = volume_mask.shape[0] // 2
                    png_path = output_path_obj.with_suffix('.png')
                    Image.fromarray((volume_mask[mid_idx] * 255).astype(np.uint8)).save(png_path)
                    click.echo(f"  Middle slice PNG: {png_path}")

                if save_probability:
                    prob_volume = np.stack([r.probability_map for r in results], axis=0)
                    prob_path = output_path_obj.with_name(f"{output_path_obj.stem}_prob.npy")
                    np.save(prob_path, prob_volume)
                    click.echo(f"  Probability map: {prob_path}")
            else:
                # Single slice
                result = result_dict['result']
                _save_segmentation_result(result, output_path, output_format, save_probability)
        else:
            # Load standard image
            from PIL import Image
            img = Image.open(input_path).convert('L')
            image = np.array(img, dtype=np.float32)

            # Run segmentation
            result = pipeline.segment(image)
            _save_segmentation_result(result, output_path, output_format, save_probability)

        click.echo(f"\n{Fore.GREEN}Segmentation complete!{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}Segmentation failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


def _save_segmentation_result(result, output_path: str, output_format: str, save_probability: bool):
    """Helper to save segmentation result."""
    from PIL import Image

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"\n{Fore.GREEN}Segmentation Results{Style.RESET_ALL}")
    click.echo(f"  Regions found: {result.num_regions}")
    click.echo(f"  Total area: {result.total_area:,} pixels")
    click.echo(f"  Threshold: {result.metadata.get('threshold', 0.5)}")
    click.echo(f"  Device: {result.metadata.get('device', 'N/A')}")

    if result.regions:
        click.echo(f"\n{Fore.YELLOW}Region Details:{Style.RESET_ALL}")
        for i, region in enumerate(result.regions[:5], 1):
            click.echo(f"  Region {i}: area={region['area']:,} px, centroid={region.get('centroid', 'N/A')}")
        if len(result.regions) > 5:
            click.echo(f"  ... and {len(result.regions) - 5} more regions")

    # Save mask
    if output_format in ['npy', 'both']:
        npy_path = output_path_obj.with_suffix('.npy')
        np.save(npy_path, result.mask)
        click.echo(f"\n  Mask (npy): {npy_path}")

    if output_format in ['png', 'both']:
        png_path = output_path_obj.with_suffix('.png')
        Image.fromarray((result.mask * 255).astype(np.uint8)).save(png_path)
        click.echo(f"  Mask (png): {png_path}")

    if save_probability:
        prob_path = output_path_obj.with_name(f"{output_path_obj.stem}_prob.npy")
        np.save(prob_path, result.probability_map)
        click.echo(f"  Probability map: {prob_path}")


@medical.command('evaluate')
@click.argument('prediction_path', type=click.Path(exists=True))
@click.argument('ground_truth_path', type=click.Path(exists=True))
@click.option('--surface-metrics', is_flag=True, help='Include Hausdorff and surface distance metrics')
def evaluate_segmentation(prediction_path: str, ground_truth_path: str, surface_metrics: bool):
    """Evaluate segmentation against ground truth mask."""
    from src.unet_segmentation import SegmentationMetrics
    from PIL import Image

    click.echo(f"{Fore.CYAN}Evaluating segmentation...{Style.RESET_ALL}\n")

    try:
        # Load masks
        pred_path = Path(prediction_path)
        gt_path = Path(ground_truth_path)

        if pred_path.suffix == '.npy':
            pred = np.load(prediction_path)
        else:
            pred = np.array(Image.open(prediction_path).convert('L')) > 127

        if gt_path.suffix == '.npy':
            gt = np.load(ground_truth_path)
        else:
            gt = np.array(Image.open(ground_truth_path).convert('L')) > 127

        # Calculate metrics
        metrics = SegmentationMetrics.evaluate(pred, gt, include_surface_metrics=surface_metrics)

        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}SEGMENTATION METRICS{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}\n")

        click.echo(f"{Fore.YELLOW}Overlap Metrics:{Style.RESET_ALL}")
        click.echo(f"  Dice Coefficient: {metrics['dice']:.4f}")
        click.echo(f"  IoU (Jaccard):    {metrics['iou']:.4f}")

        click.echo(f"\n{Fore.YELLOW}Classification Metrics:{Style.RESET_ALL}")
        click.echo(f"  Precision:    {metrics['precision']:.4f}")
        click.echo(f"  Recall:       {metrics['recall']:.4f}")
        click.echo(f"  Specificity:  {metrics['specificity']:.4f}")

        if surface_metrics:
            click.echo(f"\n{Fore.YELLOW}Surface Metrics:{Style.RESET_ALL}")
            hd = metrics.get('hausdorff_distance', float('inf'))
            asd = metrics.get('average_surface_distance', float('inf'))
            click.echo(f"  Hausdorff Distance: {hd:.2f} px" if hd != float('inf') else "  Hausdorff Distance: N/A")
            click.echo(f"  Avg Surface Dist:   {asd:.2f} px" if asd != float('inf') else "  Avg Surface Dist: N/A")

        # Quality assessment
        dice = metrics['dice']
        if dice >= 0.9:
            quality = f"{Fore.GREEN}Excellent{Style.RESET_ALL}"
        elif dice >= 0.8:
            quality = f"{Fore.GREEN}Good{Style.RESET_ALL}"
        elif dice >= 0.7:
            quality = f"{Fore.YELLOW}Acceptable{Style.RESET_ALL}"
        else:
            quality = f"{Fore.RED}Poor{Style.RESET_ALL}"

        click.echo(f"\n{Fore.YELLOW}Overall Quality:{Style.RESET_ALL} {quality}")

    except Exception as e:
        click.echo(f"{Fore.RED}Evaluation failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('info')
def medical_info():
    """Display medical imaging capabilities and dependencies."""
    from src.dicom_processor import check_dicom_available
    from src.ml_inference import check_ml_available
    from src.unet_segmentation import check_segmentation_available

    click.echo(f"{Fore.CYAN}Medical Imaging Capabilities{Style.RESET_ALL}\n")

    # DICOM support
    dicom_available = check_dicom_available()
    status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if dicom_available else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"{Fore.YELLOW}DICOM Support:{Style.RESET_ALL} {status}")
    if not dicom_available:
        click.echo(f"  Install with: pip install pydicom")

    # ML support
    ml_status = check_ml_available()
    click.echo(f"\n{Fore.YELLOW}ML Inference:{Style.RESET_ALL}")

    pytorch_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['pytorch'] else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"  PyTorch: {pytorch_status}")

    onnx_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['onnx'] else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"  ONNX Runtime: {onnx_status}")

    gpu_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['gpu'] else f"{Fore.YELLOW}CPU only{Style.RESET_ALL}"
    click.echo(f"  GPU Acceleration: {gpu_status}")

    # U-Net Segmentation
    seg_status = check_segmentation_available()
    click.echo(f"\n{Fore.YELLOW}U-Net Segmentation:{Style.RESET_ALL}")
    click.echo(f"  PyTorch: {f'{Fore.GREEN}Available{Style.RESET_ALL}' if seg_status['pytorch'] else f'{Fore.RED}Not installed{Style.RESET_ALL}'}")
    click.echo(f"  scipy: {f'{Fore.GREEN}Available{Style.RESET_ALL}' if seg_status['scipy'] else f'{Fore.RED}Not installed{Style.RESET_ALL}'}")
    click.echo(f"  scikit-image: {f'{Fore.GREEN}Available{Style.RESET_ALL}' if seg_status['scikit-image'] else f'{Fore.RED}Not installed{Style.RESET_ALL}'}")
    click.echo(f"  GPU: {f'{Fore.GREEN}Available{Style.RESET_ALL}' if seg_status['gpu'] else f'{Fore.YELLOW}CPU only{Style.RESET_ALL}'}")

    # Preprocessing dependencies
    click.echo(f"\n{Fore.YELLOW}Preprocessing:{Style.RESET_ALL}")

    try:
        import scipy
        click.echo(f"  scipy: {Fore.GREEN}Available{Style.RESET_ALL}")
    except ImportError:
        click.echo(f"  scipy: {Fore.RED}Not installed{Style.RESET_ALL}")

    try:
        import skimage
        click.echo(f"  scikit-image: {Fore.GREEN}Available{Style.RESET_ALL}")
    except ImportError:
        click.echo(f"  scikit-image: {Fore.RED}Not installed{Style.RESET_ALL}")

    click.echo(f"\n{Fore.CYAN}Install all medical dependencies:{Style.RESET_ALL}")
    click.echo(f"  pip install pydicom nibabel scipy scikit-image torch")
