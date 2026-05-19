"""Excel data inspection tool for agent.

只负责把 Excel 数据结构转成模型能读懂的文本描述。
不做任何分析判断，分析交给 Agent 自己。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from aeris.database import get_session_context
from aeris.services.file_service import FileService
from aeris.tools.base import Tool, ToolParameter, ToolResult


class InspectExcelTool(Tool):
    """Inspect Excel file structure and return a text description for LLM."""

    name = "inspect_excel"
    description = (
        "Inspect an Excel file and return a text description of its structure. "
        "Use this before analyzing Excel data to understand columns, types, and sample rows. "
        "Returns plain text suitable for LLM context."
    )
    parameters = [
        ToolParameter(
            name="file_id",
            type="integer",
            description="ID of the Excel file to inspect",
            required=True,
        ),
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: 'inspect' (structure overview), 'summary' (statistics), or 'groupby' (group aggregation). Use 'inspect' first.",
            required=True,
        ),
        ToolParameter(
            name="sheet_name",
            type="string",
            description="Sheet name (optional, default: first sheet). Call inspect first to see all sheets.",
            required=False,
        ),
        ToolParameter(
            name="group_column",
            type="string",
            description="Column to group by (required for 'groupby' action). E.g. 'region'",
            required=False,
        ),
        ToolParameter(
            name="agg_column",
            type="string",
            description="Column to aggregate (required for 'groupby' action). E.g. 'sales'",
            required=False,
        ),
        ToolParameter(
            name="agg_func",
            type="string",
            description="Aggregation function for groupby: 'sum', 'mean', 'count', 'max', 'min' (default: 'sum')",
            required=False,
        ),
    ]

    async def execute(
        self,
        file_id: int,
        action: str = "inspect",
        sheet_name: Optional[str] = None,
        group_column: Optional[str] = None,
        agg_column: Optional[str] = None,
        agg_func: Optional[str] = None,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None
            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                file_service = FileService(session)
                file_record = await file_service.get_file(user_id, file_id)

                if not file_record:
                    return ToolResult(success=False, error=f"File {file_id} not found")

                # Validate file type
                mime = file_record.mime_type or ""
                if not (
                    mime.startswith(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    or mime == "application/vnd.ms-excel"
                ):
                    return ToolResult(
                        success=False,
                        error=f"Not an Excel file. Got: {mime}",
                    )

                file_path = await file_service.get_file_path(file_record)
                if not file_path.exists():
                    return ToolResult(success=False, error="File not found on disk")

                # Read Excel
                try:
                    xls = pd.ExcelFile(file_path)
                except Exception as e:
                    return ToolResult(success=False, error=f"Failed to read Excel: {e}")

                sheets = xls.sheet_names
                selected = sheet_name if sheet_name and sheet_name in sheets else sheets[0]

                df = pd.read_excel(file_path, sheet_name=selected)

                # Route action
                if action == "inspect":
                    text = self._inspect(df, file_record.original_name, sheets, selected)
                elif action == "summary":
                    text = self._summary(df, file_record.original_name, selected)
                elif action == "groupby":
                    if not group_column or not agg_column:
                        return ToolResult(
                            success=False,
                            error="'groupby' requires both 'group_column' and 'agg_column' parameters. Use 'inspect' first to see available columns.",
                        )
                    text = self._groupby(
                        df, group_column, agg_column, agg_func or "sum", selected
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f"Unknown action: {action}. Use: inspect, summary, groupby",
                    )

                return ToolResult(success=True, data={"text": text})

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _inspect(
        self,
        df: pd.DataFrame,
        filename: str,
        all_sheets: List[str],
        current_sheet: str,
    ) -> str:
        """Build structure overview text."""
        lines = []
        lines.append(f"文件: {filename}")
        lines.append(f"Sheet: {current_sheet} (共 {len(all_sheets)} 个 sheet: {', '.join(all_sheets)})")
        lines.append(f"数据规模: {len(df)} 行 x {len(df.columns)} 列")
        lines.append("")

        # Column details
        lines.append("列信息:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = int(df[col].isnull().sum())
            null_pct = round(null_count / len(df) * 100, 1) if len(df) > 0 else 0
            unique = int(df[col].nunique())

            # Detect datetime
            is_date = pd.api.types.is_datetime64_any_dtype(df[col])
            if not is_date and df[col].dtype == "object":
                try:
                    pd.to_datetime(df[col].dropna().head(5))
                    is_date = True
                except Exception:
                    pass

            type_label = "日期" if is_date else dtype

            # Value range for numeric
            range_str = ""
            if pd.api.types.is_numeric_dtype(df[col]):
                min_v = df[col].min()
                max_v = df[col].max()
                mean_v = df[col].mean()
                range_str = f", 范围 {min_v:.2f}~{max_v:.2f}, 均值 {mean_v:.2f}"

            # Top values for low-cardinality categorical
            top_str = ""
            if df[col].dtype == "object" and unique <= 10:
                tops = df[col].value_counts().head(3).to_dict()
                top_str = f", 主要值: {', '.join([f'{k}({v})' for k, v in tops.items()])}"

            lines.append(
                f"  - {col} ({type_label}): {unique} 个唯一值, 空值 {null_count} ({null_pct}%){range_str}{top_str}"
            )

        lines.append("")

        # Sample rows
        lines.append("前 5 行样本:")
        sample_df = df.head(5).fillna("(空)")
        headers = " | ".join(str(c) for c in sample_df.columns)
        lines.append(f"| {headers} |")
        lines.append("|" + "|".join([" --- " for _ in sample_df.columns]) + "|")
        for _, row in sample_df.iterrows():
            vals = " | ".join(str(v)[:30] for v in row.values)
            lines.append(f"| {vals} |")

        lines.append("")
        lines.append(f"总空值数: {int(df.isnull().sum().sum())}")
        return "\n".join(lines)

    def _summary(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet: str,
    ) -> str:
        """Build statistical summary text."""
        lines = []
        lines.append(f"文件: {filename} / Sheet: {sheet}")
        lines.append(f"数据规模: {len(df)} 行 x {len(df.columns)} 列")
        lines.append("")

        # Numeric summary
        numeric_df = df.select_dtypes(include=["number"])
        if not numeric_df.empty:
            lines.append("数值列统计:")
            desc = numeric_df.describe()
            for col in numeric_df.columns:
                lines.append(f"  {col}:")
                for stat in ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]:
                    if stat in desc.index:
                        val = desc.loc[stat, col]
                        lines.append(f"    {stat}: {val:.2f}")
                # Additional: nulls
                nulls = int(df[col].isnull().sum())
                lines.append(f"    nulls: {nulls}")
                lines.append("")
        else:
            lines.append("无数值列")

        # Categorical summary
        cat_df = df.select_dtypes(include=["object"])
        if not cat_df.empty:
            lines.append("分类列统计:")
            for col in cat_df.columns:
                unique = int(df[col].nunique())
                nulls = int(df[col].isnull().sum())
                lines.append(f"  {col}: {unique} 个唯一值, 空值 {nulls}")
                if unique <= 10:
                    tops = df[col].value_counts().head(5).to_dict()
                    for k, v in tops.items():
                        lines.append(f"    {k}: {v}")
                lines.append("")
        else:
            lines.append("无分类列")

        return "\n".join(lines)

    def _groupby(
        self,
        df: pd.DataFrame,
        group_column: str,
        agg_column: str,
        agg_func: str,
        sheet: str,
    ) -> str:
        """Build groupby aggregation text."""
        if group_column not in df.columns:
            return f"错误: 分组列 '{group_column}' 不存在。可用列: {', '.join(df.columns)}"
        if agg_column not in df.columns:
            return f"错误: 聚合列 '{agg_column}' 不存在。可用列: {', '.join(df.columns)}"

        valid_funcs = {"sum", "mean", "count", "max", "min"}
        if agg_func not in valid_funcs:
            return f"错误: 聚合函数 '{agg_func}' 不支持。可用: {', '.join(valid_funcs)}"

        try:
            grouped = df.groupby(group_column, dropna=False)[agg_column].agg(agg_func)
        except Exception as e:
            return f"分组统计失败: {e}"

        lines = []
        lines.append(f"Sheet: {sheet}")
        lines.append(f"分组统计: {group_column} -> {agg_func}({agg_column})")
        lines.append("")

        # Sort by value desc
        grouped = grouped.sort_values(ascending=False)

        lines.append(f"| {group_column} | {agg_func}({agg_column}) |")
        lines.append(f"| --- | --- |")
        for group, val in grouped.items():
            g_str = str(group) if group is not None else "(空)"
            v_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            lines.append(f"| {g_str} | {v_str} |")

        lines.append("")
        lines.append(f"总计: {len(grouped)} 个分组")
        return "\n".join(lines)


def register_inspect_excel_tool(registry):
    """Register inspect_excel tool."""
    registry.register(InspectExcelTool())
