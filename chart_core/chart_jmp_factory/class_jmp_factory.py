#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : class_jmp_factory.py
@Author  : Link
@Time    : 2022/10/7 10:51
@Mark    : 调用并运行的地方
"""
import pandas as pd

from chart_core.chart_jmp.jmp_box import JmpBox
from chart_core.chart_jmp_factory.class_jmp_distribution import JmpDistribution
from chart_core.chart_jmp_factory.class_jmp_graph_builder import JmpGraphBuilder
from ui_component.ui_app_variable import UiGlobalVariable


class NewJmpFactory:

    @staticmethod
    def get_df_map_coord(jmp_df: pd.DataFrame) -> tuple:
        y_max = jmp_df["Y_COORD"].max()
        y_min = jmp_df["Y_COORD"].min() - 1
        x_max = jmp_df["X_COORD"].max()
        x_min = jmp_df["X_COORD"].min()
        percent = (y_max - y_min) / (x_max - x_min)
        return x_min, x_max, y_min, y_max, percent

    @staticmethod
    def get_jmp_lsl_usl(cpk_info: dict, is_dis: bool = False) -> dict:
        l_limit = cpk_info["LO_LIMIT"]
        h_limit = cpk_info["HI_LIMIT"]
        if UiGlobalVariable.JmpScreen == 0:
            l_limit = cpk_info["LO_LIMIT"]
            if isinstance(cpk_info["LO_LIMIT_TYPE"], float):
                l_limit = cpk_info["MIN"]
            h_limit = cpk_info["HI_LIMIT"]
            if isinstance(cpk_info["HI_LIMIT_TYPE"], float):
                h_limit = cpk_info["MAX"]
        if UiGlobalVariable.JmpScreen == 1:
            l_limit = cpk_info["MIN"]
            h_limit = cpk_info["MAX"]
        if UiGlobalVariable.JmpScreen == 2:
            l_limit = cpk_info["ALL_DATA_MIN"]
            h_limit = cpk_info["ALL_DATA_MAX"]
        if UiGlobalVariable.JmpScreen == 3:
            rig_x = cpk_info["STD"] * UiGlobalVariable.JmpMeanAddSubSigma
            l_limit = cpk_info["AVG"] - rig_x
            h_limit = cpk_info["AVG"] + rig_x
        # 处理limit相同的情况
        if l_limit == h_limit:
            if l_limit == 0:
                l_limit, h_limit = -0.1, 0.1
            else:
                offset = abs(l_limit) * 0.1 if abs(l_limit) > 0 else 1
                l_limit, h_limit = l_limit - offset, h_limit + offset

        step_nm = abs(h_limit - l_limit) / UiGlobalVariable.JmpBins
        if step_nm <= 0:
            step_nm = abs(h_limit) / 20 if h_limit != 0 else 0.1
        if not is_dis:
            return {
                "l_limit": round(l_limit, UiGlobalVariable.JmpPlotFloatRound),
                "h_limit": round(h_limit, UiGlobalVariable.JmpPlotFloatRound),
                "step_nm": round(step_nm, UiGlobalVariable.JmpPlotFloatRound),
            }
        return {
            "decimal": UiGlobalVariable.JmpPlotFloatRound,
            "min": round(l_limit - 8 * step_nm, UiGlobalVariable.JmpPlotFloatRound),
            "max": round(h_limit + 8 * step_nm, UiGlobalVariable.JmpPlotFloatRound),
            "l_limit": round(l_limit, UiGlobalVariable.JmpPlotFloatRound),
            "h_limit": round(h_limit, UiGlobalVariable.JmpPlotFloatRound),
            "inc": round(step_nm, UiGlobalVariable.JmpPlotFloatRound),
            "avg": round(cpk_info["AVG"], UiGlobalVariable.JmpPlotFloatRound),
        }

    @staticmethod
    def jmp_distribution(capability: dict, title: str = "dis_bar", by_columns: list = None, overlay_column: str = None, show_color_chart: bool = True) -> str:
        """
        使用Graph Builder生成带颜色叠加的分布图, 并附带统计报告
        修改后：为每个测试项生成一个图表和报告的组合，然后垂直排列所有组合。
        """
        if not capability:
            return ""

        # --- Part 0: Create combined column script if needed (once for all graphs) ---
        pre_script = ""
        final_overlay_column = overlay_column
        if by_columns and overlay_column:
            final_overlay_column = "Combined_Overlay"
            all_cols = by_columns + [overlay_column]
            cols_to_combine = sorted(list(set(col for col in all_cols if col.upper() != 'OVERLAY_GROUP')))
            formula_parts = [f':{col}' for col in cols_to_combine]
            formula = ' || "_" || '.join(formula_parts)
            pre_script = f'Current Data Table() << New Column( "{final_overlay_column}", Character, Formula( {formula} ) );\n'

        # --- Loop through each test item to create a combined graph-report view ---
        combined_item_scripts = []
        for key, row in capability.items():
            # --- Part 1B: Generate the statistical report for the current item ---
            single_item_capability = {key: row}
            report_script = NewJmpFactory.jmp_distribution_report_only(single_item_capability, title, by_columns)

            # --- Part 1A & 1C: Conditionally generate graph and combine ---
            if show_color_chart:
                # --- Part 1A: Generate the overlaid graph for the current item ---
                overlay_str = f', Overlay( :{final_overlay_column} )' if final_overlay_column else ''
                elements_str = 'Histogram( X, Legend( 5 ) )'
                if UiGlobalVariable.JmpDisPlotBox and not final_overlay_column:
                    elements_str += ', Box Plot( X, Legend( 6 ) )'

                jmp_gb = JmpGraphBuilder()
                variables_str = f'X( :"{key}" ){overlay_str}'
                
                jmp_gb.set_config(
                    f"""
                    Size( 800, 480 ),
                    Show Control Panel( 0 ),
                    Variables( {variables_str} ),
                    Elements( {elements_str} )
                    """
                )
                
                limits = NewJmpFactory.get_jmp_lsl_usl(row, is_dis=True)
                axis_params = f'Format( "Fixed Dec", 12, {limits["decimal"]} ), Min( {limits["min"]} ), Max( {limits["max"]} ), Inc( {limits["inc"]} )'
                
                ref_lines_str = ""
                if not UiGlobalVariable.JmpNoLimit:
                    ref_lines_str = f"""
                        Add Ref Line( {limits['l_limit']}, "Solid", "Medium Dark Red", "LSL({limits['l_limit']})", 2),
                        Add Ref Line( {limits['h_limit']}, "Solid", "Dark Red", "USL({limits['h_limit']})", 2 ),
                        Add Ref Line( {limits['avg']}, "Dashed", "Blue", "Mean({limits['avg']})", 1 )
                    """
                
                jmp_gb.new_dispatch(f'Dispatch(,"{key}",ScaleBox,{{{axis_params}}})')
                if ref_lines_str:
                    jmp_gb.new_dispatch(f'Dispatch(,"Graph Builder",FrameBox,{{{ref_lines_str}}})')
                
                graph_script = jmp_gb.execute(no_header=True)

                # --- Part 1C: Combine the graph and report side-by-side for the current item ---
                item_script = JmpBox.new_h_list_box(graph_script, report_script)
            else:
                item_script = report_script

            combined_item_scripts.append(item_script)

        # --- Part 2: Combine all item-specific views vertically ---
        combined_script = JmpBox.new_v_list_box(*combined_item_scripts)

        # --- Part 3: Wrap the combined view in a window ---
        window_script = JmpBox.new_window(JmpBox.new_outline_box(combined_script, title=title))

        # --- Part 4: Prepend the column creation script to the window script ---
        final_script = pre_script + window_script

        return final_script


    @staticmethod
    def jmp_distribution_report_only(capability: dict, title: str = "report", by_columns: list = None) -> str:
        """
        使用Distribution平台只生成统计报告，不显示图表
        """
        jmp_dis_reports = []
        by_column_str = ""
        if by_columns:
            by_cols = ", ".join([f':{col}' for col in by_columns])
            by_column_str = f"By( {by_cols} )"

        for key, row in capability.items():
            jmp_dis = JmpDistribution()
            limits = NewJmpFactory.get_jmp_lsl_usl(row, is_dis=True)
            cap_ans = ""
            if not UiGlobalVariable.JmpNoLimit:
                cap_ans = f"Capability Analysis( LSL( {limits['l_limit']} ), USL( {limits['h_limit']} ) )"
            
            jmp_dis.set_config("Stack( 1 )", "Automatic Recalc( 1 )", by_column_str)
            jmp_dis.new_continuous_distribution(f'Column( :"{key}" )', "Horizontal Layout( 1 )", "Vertical( 0 )", cap_ans)

            # 合理化坐标轴
            axis_params = f'Format( "Fixed Dec", 12, {limits["decimal"]} ), Min( {limits["min"]} ), Max( {limits["max"]} ), Inc( {limits["inc"]} )'
            jmp_dis.new_dispatch(f'Dispatch( {{:"{key}"}}, "1", ScaleBox, {{{axis_params}}} )')
            
            # 隐藏直方图，只保留报告
            jmp_dis.new_dispatch(f'Dispatch( {{:"{key}"}}, "Histogram", OutlineBox, {{Close( 1 )}} )')
            # 为报告添加标题
            jmp_dis.new_dispatch(f'Dispatch( , "Distributions", OutlineBox, {{Set Title( "{key} - {title}" )}} )')
            jmp_dis_reports.append(jmp_dis.execute(no_header=True))
            
        return JmpBox.new_v_list_box(*jmp_dis_reports)

    @staticmethod
    def jmp_distribution_trans_bar(capability: dict, title: str = "trans_bar", by_columns: list = None, overlay_column: str = None, show_color_chart: bool = True) -> str:
        """
        使用Graph Builder生成带颜色叠加的横向分布图, 并附带统计报告
        修改后：为每个测试项生成一个图表和报告的组合，然后垂直排列所有组合。
        """
        if not capability:
            return ""

        # --- Part 0: Create combined column script if needed (once for all graphs) ---
        pre_script = ""
        final_overlay_column = overlay_column
        if by_columns and overlay_column:
            final_overlay_column = "Combined_Overlay"
            all_cols = by_columns + [overlay_column]
            cols_to_combine = sorted(list(set(col for col in all_cols if col.upper() != 'OVERLAY_GROUP')))
            formula_parts = [f':{col}' for col in cols_to_combine]
            formula = ' || "_" || '.join(formula_parts)
            pre_script = f'Current Data Table() << New Column( "{final_overlay_column}", Character, Formula( {formula} ) );\n'

        # --- Loop through each test item to create a combined graph-report view ---
        combined_item_scripts = []
        for key, row in capability.items():
            # --- Part 1B: Generate the statistical report for the current item ---
            single_item_capability = {key: row}
            report_script = NewJmpFactory.jmp_distribution_report_only(single_item_capability, title, by_columns)

            # --- Part 1A & 1C: Conditionally generate graph and combine ---
            if show_color_chart:
                # --- Part 1A: Generate the overlaid graph for the current item ---
                overlay_str = f', Overlay( :{final_overlay_column} )' if final_overlay_column else ''
                elements_str = 'Histogram( Y, Legend( 5 ) )'
                if UiGlobalVariable.JmpDisPlotBox and not final_overlay_column:
                    elements_str += ', Box Plot( Y, Legend( 6 ) )'

                jmp_gb = JmpGraphBuilder()
                variables_str = f'Y( :"{key}" ){overlay_str}'
                
                jmp_gb.set_config(
                    f"""
                    Size( 1085, 480 ),
                    Show Control Panel( 0 ),
                    Variables( {variables_str} ),
                    Elements( {elements_str} )
                    """
                )

                limits = NewJmpFactory.get_jmp_lsl_usl(row, is_dis=True)
                axis_params = f'Format( "Fixed Dec", 12, {limits["decimal"]} ), Min( {limits["min"]} ), Max( {limits["max"]} ), Inc( {limits["inc"]} )'
                
                ref_lines_str = ""
                if not UiGlobalVariable.JmpNoLimit:
                    ref_lines_str = f"""
                        Add Ref Line( {limits['l_limit']}, "Solid", "Medium Dark Red", "LSL({limits['l_limit']})", 2),
                        Add Ref Line( {limits['h_limit']}, "Solid", "Dark Red", "USL({limits['h_limit']})", 2 ),
                        Add Ref Line( {limits['avg']}, "Dashed", "Blue", "Mean({limits['avg']})", 1 )
                    """
                
                jmp_gb.new_dispatch(f'Dispatch(,"{key}",ScaleBox,{{{axis_params}}})')
                if ref_lines_str:
                    jmp_gb.new_dispatch(f'Dispatch(,"Graph Builder",FrameBox,{{{ref_lines_str}}})')
                
                graph_script = jmp_gb.execute(no_header=True)

                # --- Part 1C: Combine the graph and report side-by-side for the current item ---
                item_script = JmpBox.new_h_list_box(graph_script, report_script)
            else:
                item_script = report_script
                
            combined_item_scripts.append(item_script)

        # --- Part 2: Combine all item-specific views vertically ---
        combined_script = JmpBox.new_v_list_box(*combined_item_scripts)

        # --- Part 3: Wrap the combined view in a window ---
        window_script = JmpBox.new_window(JmpBox.new_outline_box(combined_script, title=title))

        # --- Part 4: Prepend the column creation script to the window script ---
        final_script = pre_script + window_script
        return final_script
