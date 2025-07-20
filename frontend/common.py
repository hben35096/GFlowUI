import gradio as gr
import os
import json
import random
import shutil
import importlib
from func import functions, model_dl

self_dir = os.path.abspath(os.path.dirname(__file__))
workflow_dir = os.path.join(self_dir, 'workflow_files')
config_dir = os.path.join(self_dir, 'config_files')

main_config = functions.load_config(os.path.join(config_dir, 'main_config.yaml'))
model_config = functions.load_config(os.path.join(config_dir, main_config.get('model_config_file')))
model_names = list(model_config.keys())
model_name_a = model_names[0]
resolution_list = model_config[model_name_a].get('resolution_list')

# 例子配置，顺便把标题放一起
ex_config = functions.load_config(os.path.join(config_dir, main_config.get('ex_config_file')))
main_name = ex_config.get('main_name')
main_description = ex_config.get('main_description')
main_logo = ex_config.get('main_logo')
examples_dict = ex_config.get('examples_dict')
example_list = list(examples_dict.values())
examples_norm = [t for t in example_list]

WAN_MODELS = ["Wan2.1-T2V-1.3B-480P", "Wan2.1-T2V-14B-720P"]
HUNYUAN_MODELS = ["HunyuanVideo-T2V-720P"]

# 这里定义一下叫法
if model_name_a in WAN_MODELS:
    cfg_name = 'CFG'
    neg_prompt_display = True
elif model_name_a in HUNYUAN_MODELS:
    cfg_name = '条件引导系数'
    neg_prompt_display = False

div_line = "-" * 50

def get_workflow(model, scale):
    workflow_file = f'{model}.json'
    workflow_path = os.path.join(workflow_dir, workflow_file) # 工作流文件路径
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
    # 拆分成宽和高
    width_str, height_str = scale.split("x")
    width = int(width_str)
    height = int(height_str)
    return workflow, width, height

def edit_workflow(model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed):
    workflow, width, height = get_workflow(model, scale)

    if model in WAN_MODELS:
        workflow["6"]["inputs"]["text"] = prompt_input
        workflow["7"]["inputs"]["text"] = neg_prompt_input
        
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["seed"] = seed
        workflow["3"]["inputs"]["cfg"] = cfg
    
        workflow["40"]["inputs"]["width"] = width
        workflow["40"]["inputs"]["height"] = height
        workflow["40"]["inputs"]["length"] = length
        workflow["40"]["inputs"]["batch_size"] = batch_size
    elif model in HUNYUAN_MODELS:
        workflow["44"]["inputs"]["text"] = prompt_input
        
        workflow["17"]["inputs"]["steps"] = steps
        
        workflow["25"]["inputs"]["noise_seed"] = seed
        workflow["26"]["inputs"]["guidance"] = cfg #
    
        workflow["45"]["inputs"]["width"] = width
        workflow["45"]["inputs"]["height"] = height
        workflow["45"]["inputs"]["length"] = length
        workflow["45"]["inputs"]["batch_size"] = batch_size

    return workflow

def model_switch(model_name=None):
    info_t = f"已选择模型 {model_name}"
    gr.Info(info_t, duration=3)
    
    resolution_list = model_config[model_name].get('resolution_list')
    return gr.update(choices=resolution_list, value=resolution_list[0])

def seed_update(seed, seed_fixed):
    if seed_fixed == "🎲":
        seed = random.randint(1, 999999999999999)
    return gr.update(value=seed)

def video_generate(launch_state, model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, queue_size):
    from frontend import to_api
    importlib.reload(to_api) # 实时更改生效，以后就不需要了

    app_url, back_app_path, dl_way = launch_state

    target_path = None
    model_dl_dict = model_config[model].get('download_way')
    model_dl.check_models(back_app_path, model_dl_dict, dl_way) # 检测模型
    gr.Info("任务已提交，可以到后台查看任务进度", duration=3)
    for i in range(queue_size):
        print(f"列队任务：{i+1}/{queue_size}")
        if i > 0:
            seed = random.randint(1, 999999999999999)
        # print("现在的种子：", seed)
        workflow = edit_workflow(model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed)
        
        output_file_path_list = to_api.implement(workflow, app_url, back_app_path)
    
        video_path = output_file_path_list
        if isinstance(output_file_path_list, list):
            video_path = output_file_path_list[0]
        # 要复制到工作目录才行
        output_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = os.path.basename(video_path)
        target_path = os.path.join(output_dir, filename)
        shutil.copy(video_path, target_path)
        print("生成文件已保存到：", target_path)
        print(div_line)
    
    return target_path
    # 循环结束才返回路径，路径一直被覆盖的，所以是在循环结束，才会显示最后的视频

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""
# js_func = None

generate_btn_css="""
.custom-btn {
    height: 98px;
    font-size: 18px;
}
"""

# 如果是热加载，不能放 def 里面的
def gradio_ui(app_url, back_app_path, dl_way):

    with gr.Blocks(theme="soft", js=js_func, css=generate_btn_css) as demo:
        gr.HTML(f"""
        <div style="display: flex; align-items: center; justify-content: flex-start; gap: 12px; margin-bottom: 1.5em;">
          <img src={main_logo} 
               alt="Logo" style="height: 48px; auto;">
          <div>
            <div style="font-size: 22px; font-weight: bold;">{main_name}</div>
            <div style="font-size: 14px; color: gray;">{main_description}</div>
          </div>
        </div>
        """)
        with gr.Row():
            with gr.Column(scale=3):
                # gr.Markdown("#### 可选参数")
                model = gr.Dropdown(choices=model_names, label="模型")
                with gr.Group():
                    scale = gr.Dropdown(choices=resolution_list, label="分辨率(宽×高)",)
                    steps = gr.Slider(value=30, label='迭代步数 Steps', minimum=1, maximum=128, step=1)
                    cfg = gr.Slider(value=4.0, label=cfg_name, maximum=32, step=0.1)
                    length = gr.Slider(value=33, label='生成帧数', minimum=33, maximum=129, step=16)
                    batch_size = gr.Slider(value=1, label='单批数量', maximum=16, step=1, interactive=False, info="当前模式下批次大小不可修改") # 禁用吧
                    
                with gr.Row():
                    seed = gr.Number(value=0, label='随机种子 Seed', precision=0, step=1, min_width=140, scale=6)
                    seed_fixed = radio = gr.Radio(choices=["📌", "🎲"], show_label=False, value="🎲", min_width=20, scale=2)
            with gr.Column(scale=10, min_width=320): # , scale=10
                with gr.Row():
                    with gr.Column(scale=8):
                        with gr.Row():
                            prompt_input = gr.Textbox(
                                label="提示词", placeholder="正向提示词 Positive Prompt", show_label=False, container=False, lines=4, max_lines=8, scale=4
                            ) 
                            neg_prompt_input = gr.Textbox(
                                placeholder="反向提示词 Negative Prompt", show_label=False,  container=False, lines=4, max_lines=8, scale=4, visible=neg_prompt_display
                            )
                        examples = gr.Examples(label="提示词示例:", examples=examples_norm, inputs=[prompt_input, neg_prompt_input], example_labels=list(examples_dict.keys()),) 
    
                    with gr.Column(scale=1, min_width=160): # , min_width=160
                        generate_btn = gr.Button("生成视频", variant="primary", elem_classes="custom-btn")
                        gr.Markdown("##### 批量生成：")
                        queue_size = gr.Number(value=1, label='列队数量', precision=0, minimum=1, step=1, scale=1, container=False, min_width=126)
                video_output = gr.Video(label="Output Video", height=450, show_download_button=True, interactive=False)
                
        launch_state = gr.State(value=(app_url, back_app_path, dl_way)) # 多个参数放这里方便传递
        
        generate_btn.click(
            fn=video_generate,
            inputs=[launch_state, model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, queue_size],
            outputs=[video_output] # video_output, 暂时不要
        ).success(fn=seed_update, inputs=[seed, seed_fixed], outputs=[seed])
        model.select(fn=model_switch, inputs=[model], outputs=[scale])

    return demo

if __name__ == "__main__":
    demo.launch()

