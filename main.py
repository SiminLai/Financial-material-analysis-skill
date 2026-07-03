from providers.llm_provider import LLMProvider
from providers.pdf_provider import PDFProvider
from providers.excel_provider import ExcelProvider

from tools.pdf_parser_tool import PDFParserTool
from tools.excel_parser_tool import ExcelParserTool
from tools.document_parser_tool import DocumentParserTool
from tools.metric_extractor_tool import MetricExtractorTool
from tools.risk_detection_tool import RiskDetectionTool
from tools.report_generator_tool import ReportGeneratorTool

from workflow.financial_workflow import FinancialWorkflow
from skills.financial_analysis_skill import FinancialAnalysisSkill

from state.workflow_state import WorkflowState

def main():
    llm_provider = LLMProvider("deepseek-v4-flash",api_key="")
    pdf_provider = PDFProvider()
    excel_provider = ExcelProvider()

    pdf_tool = PDFParserTool(pdf_provider)
    excel_tool = ExcelParserTool(excel_provider)
    document_tool = DocumentParserTool(pdf_tool, excel_tool)
    metric_tool = MetricExtractorTool(llm_provider)
    risk_tool = RiskDetectionTool(llm_provider)
    report_tool = ReportGeneratorTool(llm_provider)

    workflow = FinancialWorkflow(
        tools={
            "parser": document_tool,
            "metric": metric_tool,
            "risk": risk_tool,
            "report": report_tool
        }
    )

    skill = FinancialAnalysisSkill(workflow)

    result = skill.invoke(r"examples\2025-11-05_Texas_Pacific_Land_Corporation_Announces_Third_174.pdf")

    print(result)


if __name__ == "__main__":
    main()