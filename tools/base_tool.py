from abc import ABC, abstractmethod
from typing import Any

from validators import validate_payload


class BaseTool(ABC):

    name: str = ""
    description: str = ""

    input_schema = None
    output_schema = None


    # 同步入口
    def invoke(
        self,
        input_data: Any
    ) -> Any:


        self.validate_input(input_data)

        result = self._execute(input_data)

        self.validate_output(result)

        return result



    # 异步入口
    async def ainvoke(
        self,
        input_data: Any
    ) -> Any:


        self.validate_input(input_data)

        result = await self._aexecute(input_data)

        self.validate_output(result)

        return result



    # 同步Tool实现
    def _execute(
        self,
        input_data
    ):

        raise NotImplementedError



    # 异步Tool实现
    async def _aexecute(
        self,
        input_data
    ):

        raise NotImplementedError



    def validate_input(self,input_data):

        if self.input_schema:

            validate_payload(
                input_data,
                self.input_schema,
                field_name="tool_input"
            )


    def validate_output(self,output_data):

        if self.output_schema:

            validate_payload(
                output_data,
                self.output_schema,
                field_name="tool_output"
            )