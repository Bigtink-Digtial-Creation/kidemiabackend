"""
Enhanced Analytics API Routes - With Working Downloads
Developed By Samuel Kufre Willie - 31 January 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from src.config.database import get_db
from src.core.security import get_current_user_id, require_permissions
from src.domains.report.services.analytics_service import AnalyticsService
from src.domains.report.utils.report_exporter import ReportExporter
from src.domains.report.schemas.analytics import (
    DashboardResponse,
    AssessmentAnalyticsResponse,
    StudentPerformanceResponse,
    FinancialOverviewResponse,
    QuestionQualityResponse,
    ReportGenerationRequest,
    ExportFormat,
)

from src.domains.access_control.dependency import RequireAccess
from src.domains.access_control.schema import ACCESS_RESPONSES
from src.domains.access_control.core import AccessResult

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/report/admin", response_model=DashboardResponse)
async def get_admin_dashboard(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get comprehensive admin dashboard analytics"""
    service = AnalyticsService(db)
    data = await service.get_admin_dashboard_data()
    return data


@router.get(
    "/report/student/{student_id}",
    response_model=StudentPerformanceResponse,
    responses={**ACCESS_RESPONSES},
)
async def get_student_dashboard(
    student_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    access: AccessResult = Depends(
        RequireAccess(
            resource="analytics",
            feature="progress_tracking",
            feature_only=True,
            auto_charge=False,
        )
    ),
):
    """Get enhanced student-specific dashboard analytics with topic-level data"""
    service = AnalyticsService(db)
    data = await service.get_student_dashboard_data(student_id)
    return data


@router.get("/students/{student_id}/topics")
async def get_student_topic_analytics(
    student_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get detailed topic-level analytics for a student"""
    service = AnalyticsService(db)
    data = service.get_topic_analytics(student_id)
    return data


@router.get("/students/{student_id}/topics/{topic_id}/trend")
async def get_topic_trend(
    student_id: UUID,
    topic_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get performance trend for a specific topic"""
    service = AnalyticsService(db)
    data = service.get_topic_analytics(student_id, topic_id)
    return data


@router.get("/students/{student_id}/study-plan")
async def get_student_study_plan(
    student_id: UUID,
    duration_days: int = Query(14, ge=7, le=30),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get personalized study plan for student"""
    service = AnalyticsService(db)
    plan = service.repo.generate_personalized_study_plan(student_id, duration_days)
    return {
        "study_plan": plan,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/reports/generate")
async def generate_report(
    request: ReportGenerationRequest,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """
    Generate comprehensive report for export

    Supports formats: PDF, Excel, CSV, JSON
    Returns downloadable file or JSON data
    """
    service = AnalyticsService(db)
    exporter = ReportExporter()

    # Generate report data
    data = service.generate_comprehensive_report(
        report_type=request.report_type,
        entity_id=request.entity_id,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    # Return JSON if requested
    if request.format == ExportFormat.JSON:
        return data

    # Generate file for download
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kidemia_{request.report_type}_{timestamp}"

    try:
        if request.format == ExportFormat.CSV:
            output = exporter.export_to_csv(data, request.report_type)
            media_type = "text/csv"
            filename += ".csv"
            content = output.getvalue()

        elif request.format == ExportFormat.EXCEL:
            output = exporter.export_to_excel(data, request.report_type)
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename += ".xlsx"
            content = output.getvalue()

        elif request.format == ExportFormat.PDF:
            output = exporter.export_to_pdf(data, request.report_type)
            media_type = "application/pdf"
            filename += ".pdf"
            content = output.getvalue()

        else:
            raise HTTPException(status_code=400, detail="Invalid export format")

        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content)),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating report: {str(e)}"
        )


@router.get("/reports/download/csv/{report_type}")
async def download_csv_report(
    report_type: str,
    entity_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Quick download CSV report"""
    service = AnalyticsService(db)
    exporter = ReportExporter()

    data = service.generate_comprehensive_report(
        report_type=report_type, entity_id=entity_id
    )

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    output = exporter.export_to_csv(data, report_type)
    content = output.getvalue()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kidemia_{report_type}_{timestamp}.csv"

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(content)),
        },
    )


@router.get("/reports/download/excel/{report_type}")
async def download_excel_report(
    report_type: str,
    entity_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Quick download Excel report"""
    service = AnalyticsService(db)
    exporter = ReportExporter()

    data = service.generate_comprehensive_report(
        report_type=report_type, entity_id=entity_id
    )

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    output = exporter.export_to_excel(data, report_type)
    content = output.getvalue()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kidemia_{report_type}_{timestamp}.xlsx"

    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(content)),
        },
    )


@router.get("/reports/download/pdf/{report_type}")
async def download_pdf_report(
    report_type: str,
    entity_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Quick download PDF report"""
    service = AnalyticsService(db)
    exporter = ReportExporter()

    data = service.generate_comprehensive_report(
        report_type=report_type, entity_id=entity_id
    )

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    output = exporter.export_to_pdf(data, report_type)
    content = output.getvalue()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kidemia_{report_type}_{timestamp}.pdf"

    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(content)),
        },
    )


@router.get("/report/guardian/{guardian_id}")
async def get_guardian_dashboard(
    guardian_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get guardian dashboard showing all wards' performance"""
    service = AnalyticsService(db)
    data = service.get_guardian_dashboard_data(guardian_id)
    return data


@router.get("/report/institution/{institution_id}")
async def get_institution_dashboard(
    institution_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get institution-specific analytics"""
    service = AnalyticsService(db)
    data = await service.get_institution_dashboard_data(institution_id)
    return data


@router.get("/assessments/{assessment_id}", response_model=AssessmentAnalyticsResponse)
async def get_assessment_analytics(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get detailed analytics for a specific assessment"""
    service = AnalyticsService(db)
    data = await service.get_assessment_analytics(assessment_id)

    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])

    return data


@router.get("/assessments/category/comparison")
async def get_category_comparison(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Compare performance across assessment categories"""
    service = AnalyticsService(db)
    data = await service.get_assessment_category_comparison()
    return data


@router.get("/assessments/top-performing")
async def get_top_assessments(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get top performing assessments by average score"""
    service = AnalyticsService(db)
    data = service.repo.get_top_performing_assessments(limit=limit)
    return {"assessments": data}


@router.get("/assessments/most-difficult")
async def get_difficult_assessments(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get assessments with lowest pass rates"""
    service = AnalyticsService(db)
    data = service.repo.get_difficult_assessments(limit=limit)
    return {"assessments": data}


@router.get("/questions/quality-report", response_model=QuestionQualityResponse)
async def get_question_quality_report(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Analyze question quality and difficulty accuracy"""
    service = AnalyticsService(db)
    data = await service.get_question_quality_report()
    return data


@router.get("/questions/most-missed")
async def get_most_missed_questions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get questions with lowest success rates"""
    service = AnalyticsService(db)
    data = service.repo.get_most_missed_questions(limit=limit)
    return {"questions": data}


@router.get("/financial/overview", response_model=FinancialOverviewResponse)
async def get_financial_overview(
    period: str = Query("monthly", pattern="^(monthly|quarterly|yearly)$"),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get comprehensive financial analytics"""
    service = AnalyticsService(db)
    data = await service.get_financial_overview(period=period)
    return data


@router.get("/financial/revenue-trend")
async def get_revenue_trend(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get revenue trend over specified period"""
    service = AnalyticsService(db)
    data = service.repo.get_revenue_by_period(days=days)
    return {"trend": data}


@router.get("/financial/subscriptions")
async def get_subscription_analytics(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get subscription-related metrics"""
    service = AnalyticsService(db)
    data = service.repo.get_subscription_analytics()
    return data


@router.get("/engagement/overview")
async def get_engagement_overview(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get platform-wide engagement metrics"""
    service = AnalyticsService(db)
    data = await service.get_platform_engagement_report()
    return data


@router.get("/engagement/user-growth")
async def get_user_growth(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get user registration trends"""
    service = AnalyticsService(db)
    data = service.repo.get_user_growth_data(days=days)
    return {"growth": data}


@router.get("/students/{student_id}/performance")
async def get_student_performance(
    student_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get comprehensive performance summary for a student"""
    service = AnalyticsService(db)
    data = service.repo.get_student_performance_summary(student_id)
    return data


@router.get("/students/{student_id}/subject-performance")
async def get_student_subject_performance(
    student_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get student performance breakdown by subject"""
    service = AnalyticsService(db)
    data = service.repo.get_student_subject_performance(student_id)
    return {"subjects": data}


@router.get("/students/{student_id}/progress")
async def get_student_progress(
    student_id: UUID,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get student's score progression over time"""
    service = AnalyticsService(db)
    data = service.repo.get_student_progress_over_time(student_id, days=days)
    return {"progress": data}


@router.get("/students/{student_id}/prediction")
async def get_performance_prediction(
    student_id: UUID,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Predict student's future performance based on trends"""
    service = AnalyticsService(db)
    data = await service.predict_student_performance(student_id)
    return data


@router.get("/realtime/activity")
async def get_realtime_activity(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get recent platform activities for real-time monitoring"""
    service = AnalyticsService(db)
    activities = service.get_realtime_activity_feed(limit=limit)
    return {"activities": activities}


@router.get("/overview")
async def get_platform_overview(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _: None = Depends(require_permissions("report:read")),
):
    """Get high-level platform statistics"""
    service = AnalyticsService(db)
    data = service.repo.get_platform_overview()
    return data
