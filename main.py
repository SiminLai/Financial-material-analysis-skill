import asyncio


from providers.llm_provider import LLMProvider
from providers.pdf_provider import PDFProvider
from providers.excel_provider import ExcelProvider


from tools.pdf_parser_tool import PDFParserTool
from tools.excel_parser_tool import ExcelParserTool
from tools.document_parser_tool import DocumentParserTool
from tools.metric_extractor_tool import MetricExtractorTool
from tools.risk_detection_tool import RiskDetectionTool
from tools.report_generator_tool import ReportGeneratorTool


from graph.financial_graph import create_finance_graph


from mcp_local.manager import MCPManager



async def main():

    mcp_manager = MCPManager(
        "config/mcp.json"
    )

    try:

        # await mcp_manager.register_browser()

        # browser_tool = mcp_manager.get_tool(
        #     "browser"
        # )

        await mcp_manager.register(
            "tavily"
        )


        search_tool = mcp_manager.get_tool(
            "tavily"
        )


        llm_provider = LLMProvider(
            "deepseek-v4-flash",
            api_key=""
        )


        pdf_provider = PDFProvider()
        excel_provider = ExcelProvider()


        pdf_tool = PDFParserTool(
            pdf_provider
        )

        excel_tool = ExcelParserTool(
            excel_provider
        )


        parser_tool = DocumentParserTool(
            pdf_tool,
            excel_tool
        )


        metric_tool = MetricExtractorTool(
            llm_provider
        )


        risk_tool = RiskDetectionTool(
            llm_provider
        )


        report_tool = ReportGeneratorTool(
            llm_provider
        )


        # graph = create_finance_graph(
        #     parser_tool=parser_tool,
        #     metric_tool=metric_tool,
        #     risk_tool=risk_tool,
        #     browser_tool=browser_tool,
        #     report_tool=report_tool
        # )

        graph = create_finance_graph(
            parser_tool=parser_tool,
            metric_tool=metric_tool,
            risk_tool=risk_tool,
            browser_tool=search_tool,
            report_tool=report_tool
        )


        result = await graph.ainvoke(
            {
                "input_file":
                r"examples\Q4'25+EarningsRelease+FINAL+v1.pdf"
            }
        )


        print(result["report"])


    finally:

        await mcp_manager.close()


if __name__ == "__main__":

    asyncio.run(main())