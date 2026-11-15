"""CLI safety without NASA substitutions."""
import os,subprocess,sys
from pathlib import Path

def test_cli_refuses_existing_output(tmp_path):
    output=tmp_path/'result.json';output.write_text('preserve')
    result=subprocess.run([sys.executable,'-m','data_pipeline.visibility_cli','--request',str(tmp_path/'absent'),'--output',str(output)],capture_output=True,text=True)
    assert result.returncode!=0 and 'Refusing to overwrite' in result.stderr
    assert output.read_text()=='preserve'

def test_cli_help_documents_real_flags():
    result=subprocess.run([sys.executable,'-m','data_pipeline.visibility_cli','--help'],capture_output=True,text=True)
    assert result.returncode==0
    assert all(flag in result.stdout for flag in ['--request','--output','--count','--step-seconds','--use-20m'])
