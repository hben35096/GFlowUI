import gradio as gr
import os
import json
import random
import shutil
import importlib
from func import functions, model_dl

div_line = "-" * 50

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
FLUX_MODELS = ["Flux-T2I-FP16"]

NO_CFG_MODELS = HUNYUAN_MODELS + FLUX_MODELS


KSAMPLER_NAMES = [
    "euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp", "heun", "heunpp2","dpm_2", "dpm_2_ancestral",
    "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu", "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm",
    "ipndm", "ipndm_v", "deis", "res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral", "res_multistep_ancestral_cfg_pp",
    "gradient_estimation", "gradient_estimation_cfg_pp", "er_sde", "seeds_2", "seeds_3"
]
SAMPLER_NAMES = KSAMPLER_NAMES + ["ddim", "uni_pc", "uni_pc_bh2"]

# 这里定义一下叫法
if model_name_a in NO_CFG_MODELS:
    cfg_name = '条件引导系数'
    neg_prompt_display = False
else:
    cfg_name = 'CFG'
    neg_prompt_display = True

def img_display(model_name):
    model_type = model_config[model_name].get('model_type')
    if model_type in ["I2V", "I2I"]:
        return True
    else:
        return False
        
input_img_display = img_display(model_name_a)

def clear_outputs():
    return None

def model_switch(model_name=None):
    info_t = f"已选择模型 {model_name}"
    gr.Info(info_t, duration=3)
    
    resolution_list = model_config[model_name].get('resolution_list')
    input_img_display = img_display(model_name)
    
    return gr.update(choices=resolution_list, value=resolution_list[0]), input_img_display, gr.update(visible=input_img_display)
    # 更新给 分辨率列表、输入图片存储、输入图片显示项

def seed_update(seed, seed_fixed, all_output):
    if seed_fixed == "🎲" and all_output is not None:
        seed = random.randint(1, 999999999999999)
    return gr.update(value=seed)

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

def edit_workflow(model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, input_imgs=None, sampler_name=None):
    workflow, width, height = get_workflow(model, scale)
    # print("看看采样器名称：", sampler_name)

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
    elif model == "LTX-098-I2V-13B":
        workflow["6"]["inputs"]["text"] = prompt_input
        workflow["7"]["inputs"]["text"] = neg_prompt_input
        workflow["71"]["inputs"]["steps"] = steps
        
        workflow["72"]["inputs"]["noise_seed"] = seed
        workflow["72"]["inputs"]["cfg"] = cfg
        
        workflow["95"]["inputs"]["width"] = width
        workflow["95"]["inputs"]["height"] = height
        workflow["95"]["inputs"]["length"] = length
        workflow["95"]["inputs"]["batch_size"] = batch_size

        workflow["78"]["inputs"]["image"] = input_imgs
    # 暂时没有
    elif model == "LTX-098-T2V-13B":
        workflow["6"]["inputs"]["text"] = prompt_input
        workflow["7"]["inputs"]["text"] = neg_prompt_input
        workflow["71"]["inputs"]["steps"] = steps
        workflow["72"]["inputs"]["noise_seed"] = seed
        workflow["72"]["inputs"]["cfg"] = cfg

        workflow["70"]["inputs"]["width"] = width
        workflow["70"]["inputs"]["height"] = height
        workflow["70"]["inputs"]["length"] = length
        workflow["70"]["inputs"]["batch_size"] = batch_size
    elif model == "Flux-T2I-FP16":
        workflow["6"]["inputs"]["text"] = prompt_input
        workflow["17"]["inputs"]["steps"] = steps
        workflow["25"]["inputs"]["noise_seed"] = seed
        workflow["26"]["inputs"]["guidance"] = cfg
        
        workflow["27"]["inputs"]["width"] = width
        workflow["27"]["inputs"]["height"] = height
        workflow["27"]["inputs"]["batch_size"] = batch_size
        
        workflow["16"]["inputs"]["sampler_name"] = sampler_name

    return workflow



def video_generate(launch_state, img_display_state, model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, queue_size, input_imgs=None, sampler_name=None):
    from frontend import to_api
    importlib.reload(to_api) # 实时更改生效，以后就不需要了

    app_url, back_app_path, dl_way = launch_state
    
    workflow_model_name = model
    if model == "LTX-098-I2V-13B" and input_imgs is None:
        workflow_model_name = "LTX-098-T2V-13B"

    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    all_output_file_path = []
    model_dl_dict = model_config[model].get('download_way')
    model_dl.check_models(back_app_path, model_dl_dict, dl_way) # 检测模型
    gr.Info("任务已提交，可以到后台查看任务进度", duration=10)
    for i in range(queue_size):
        print(f"列队任务：{i+1}/{queue_size}")
        if i > 0:
            seed = random.randint(1, 999999999999999)

        workflow = edit_workflow(workflow_model_name, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, input_imgs, sampler_name)
        
        output_file_path_list = to_api.implement(workflow, app_url, back_app_path)
        # 要复制到工作目录才行
        for generate_file_path in output_file_path_list:
            filename = os.path.basename(generate_file_path)
            target_path = os.path.join(output_dir, filename)
            shutil.copy(generate_file_path, target_path)
            if os.path.exists(target_path):
                print("生成文件已保存到：", target_path)
                all_output_file_path.append(target_path)
        print(div_line)
        
    if len(all_output_file_path) > 6:
        tip_inf = f"提示：批量生成的数量较多，只显示最后 6 个，所有生成文件，可以到 {output_dir} 目录下查看"
        gr.Info(tip_inf, duration=3)
        print(tip_inf)
    display_outputs = all_output_file_path[-6:]
    return display_outputs

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
    height: 90px;
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
                    steps = gr.Slider(value=20, label='迭代步数 Steps', minimum=1, maximum=128, step=1)
                    cfg = gr.Slider(value=2.5, label=cfg_name, maximum=32, step=0.1)
                    length = gr.Slider(value=97, label='生成帧数', minimum=25, maximum=1441, step=24, visible=False) # 用不着了
                    sampler_name = gr.Dropdown(choices=SAMPLER_NAMES, label="采样器",)
                    batch_size = gr.Slider(value=1, label='单批数量', minimum=1, maximum=16, step=1, interactive=True) # 禁用吧 , info="当前模式下批次大小不可修改"
                    
                with gr.Row():
                    seed = gr.Number(value=0, label='随机种子 Seed', precision=0, step=1, min_width=140, scale=6)
                    seed_fixed = radio = gr.Radio(choices=["📌", "🎲"], show_label=False, value="🎲", min_width=20, scale=2)
            with gr.Column(scale=10, min_width=320): # , scale=10
                with gr.Row():
                    # with gr.Column(scale=8):
                    #     with gr.Row():
                    prompt_input = gr.Textbox(
                        label="提示词", placeholder="正向提示词 Positive Prompt", show_label=False, container=False, lines=8, max_lines=8, scale=4
                    ) 
                    neg_prompt_input = gr.Textbox(
                        placeholder="反向提示词 Negative Prompt", show_label=False,  container=False, lines=8, max_lines=8, scale=4, visible=neg_prompt_display
                    )
    
                    with gr.Column(scale=1, min_width=160): # , min_width=160
                        generate_btn = gr.Button("生 成", variant="primary", elem_classes="custom-btn")
                        gr.Markdown("##### 批量生成：")
                        queue_size = gr.Number(value=1, label='列队数量', precision=0, minimum=1, step=1, scale=1, container=False, min_width=126)
                with gr.Column() as examples_container:
                    # 先占位置
                    pass
                with gr.Row():
                    input_img = gr.Image(label="上传参考图-如果不上传参考图，则采用文生视频模式", type="filepath", height=432, visible=input_img_display)  # 暂时不显示，也不调用
                    all_output = gr.Gallery(label="生成结果", columns=3, object_fit="contain", interactive=False, height=432, selected_index=0, preview=True, scale=2)

        with examples_container:
            examples = gr.Examples(label="提示词示例:", examples=examples_norm, inputs=[prompt_input, neg_prompt_input, input_img], example_labels=list(examples_dict.keys()),)
                                    
        launch_state = gr.State(value=(app_url, back_app_path, dl_way)) # 多个参数放这里方便传递
        img_display_state = gr.State(input_img_display) # 用它来记录吧，别用全局，其实最后没用到
        inf = gr.Info()

        clear_outputs_kwargs = {
            "fn": clear_outputs,
            "inputs": [],
            "outputs": [all_output]
        }
        
        generate_kwargs = {
            "fn": video_generate,
            "inputs": [launch_state, img_display_state, model, prompt_input, neg_prompt_input, scale, steps, cfg, length, batch_size, seed, queue_size, input_img] + [sampler_name],
            "outputs": [all_output]
        }
        
        seed_update_kwargs = {
            "fn": seed_update,
            "inputs": [seed, seed_fixed, all_output],
            "outputs": [seed]
        }

        # 用字典是方便很多
        generate_btn.click(**clear_outputs_kwargs).success(**generate_kwargs).success(**seed_update_kwargs)
        model.select(fn=model_switch, inputs=[model], outputs=[scale, img_display_state, input_img])

    return demo

if __name__ == "__main__":
    demo.launch()