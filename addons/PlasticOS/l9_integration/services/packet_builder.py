def build_intake_packet(
    intake,
    packet_id: str,
    packet_version: str,
    event_type: str,
    correlation_id: str,
    run_id: str,
):
    return {
        "packet_id": packet_id,
        "packet_version": packet_version,
        "event_type": event_type,
        "correlation_id": correlation_id,
        "trace_run_id": run_id,
        "payload": {
            "intake": {
                "id": intake.id,
                "name": intake.name,
                "partner_id": intake.partner_id.id if intake.partner_id else None,
                "facility_id": intake.facility_id.id if hasattr(intake, "facility_id") and intake.facility_id else None,
                "processing_profile_id": intake.processing_profile_id.id if hasattr(intake, "processing_profile_id") and intake.processing_profile_id else None,
            },
            "material_snapshot": {
                "polymer": intake.polymer,
                "form": intake.form,
                "color": intake.color,
                "source_type": intake.source_type,
                "grade_hint": intake.grade_hint,
            },
            "observed_quality": {
                "mfi_value": intake.mfi_value,
                "density_value": intake.density_value,
                "moisture_ppm": intake.moisture_ppm,
                "contamination_total_pct": intake.contamination_total_pct,
                "has_metal": intake.has_metal,
                "has_fr": intake.has_fr,
                "has_residue": intake.has_residue,
                "filler_type": intake.filler_type,
                "filler_pct": intake.filler_pct,
                "contamination_notes": intake.contamination_notes,
            },
            "origin": {
                "origin_application": intake.origin_application,
                "origin_sector": intake.origin_sector,
                "origin_process_type": intake.origin_process_type,
            },
            "commercial": {
                "quantity_per_load_lbs": intake.quantity_per_load_lbs,
                "loads_per_month": intake.loads_per_month,
                "deal_type": intake.deal_type,
                "contract_duration_months": intake.contract_duration_months,
            },
            "freeform": {
                "material_hint_text": intake.material_hint_text,
            },
        },
    }
