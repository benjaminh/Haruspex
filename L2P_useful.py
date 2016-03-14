#!/usr/bin/env python3
# encoding: utf-8
from os import walk, getcwd, chdir, makedirs
from os.path import splitext, isfile, join, split, abspath, exists
import re
import subprocess

def setup_dir():
    if not exists(join('pages', 'convertconcat', 'convert')):
    	makedirs(join('pages', 'convertconcat', 'convert'))
    if not exists(join('pages','BeingClean')):
    	makedirs(join('pages','BeingClean'))
    if not exists(join('pages','output')):
    	makedirs(join('pages','output'))

# conversion of odt file into minimal tex
def writer2latex(writer2LaTeX_path, odt_file_names, outputconvert, working_directory):
    origWD = getcwd() #remember original WorkingDirectory
    try:
        chdir(writer2LaTeX_path)
        for filename in odt_file_names:
            arguments = ['-config', join('config', 'preANA.xml'),
                join(working_directory, filename+'.odt'),#the input odt file path
                join(outputconvert, filename+'.tex')]#the output tex file in a subfolder
            subprocess.call(['java', '-jar', 'writer2latex.jar'] + arguments)
        chdir(origWD)
    except FileNotFoundError:
        print("Didnt found writer2latex, processing…")

def concatenate(odt_file_names, tex_files, output):#only concatenate the  tex or .odt files run in a first time (before processing them and before processing the non tex nor odt ones)
    concat_filepath = join(output, 'concat.tex')
    with open(concat_filepath, 'w') as concat_file:
        for odt_file_name in odt_file_names:
            converted_texfilepath = join(output, 'convert', odt_file_name+'.tex')
            concat_file.write('\\filename{' + odt_file_name +'.odt}\n')#a new latex-like marker for the page process
            with open(converted_texfilepath) as infile:
                for line in infile:
                    concat_file.write(line)
        for filepath in tex_files:
            concat_file.write('\\filename{' + filepath + '}\n')#a new latex-like marker for the page process
            with open(filepath) as infile:
                for line in infile:
                    concat_file.write(line)

def concatenate2(other_files, output):#concatenate the "other files" (non tex, nor .odt) run in a second time (after having processed all the tex and odt files)
    concat_filepath = join(output, 'concat.tex')
    with open(concat_filepath, 'a') as concat_file:
        for txtfile_name in other_files:
            concat_file.write('\\filename{' + txtfile_name + '}\n')#a new latex-like marker for the page process
            with open(txtfile_name) as infile:
                for line in infile:
                    line = re.sub(r'ʽ|՚|‘|‛|‵|ʾ|\'|ʿ|ʼ|΄|´|´|′|Ꞌ|ꞌ|ʹ|ˈ|‘|’|ʽ|ʼ|’', '\'', line)#this is done for the tex and odt files, but we need to purge the diacritics averywhere!
                    concat_file.write(line)


def convert_concat(working_directory, writer2LaTeX_path):
    output = join(working_directory, 'pages', 'convertconcat')
    outputconvert = join(output, 'convert')#so it is pathtoworking_directory/concat_convert/convert
    txt_files = set()
    odt_file_names = set()
    tex_files = set()
    for f in next(walk(working_directory))[2]:#file_list is a list of NON-absolute path to original files in working dir
        filename, file_extension = splitext(f)
        if file_extension == '.odt':
            odt_file_names.add(filename)
        if file_extension == '.tex':
            tex_files.add(f)
    writer2latex(writer2LaTeX_path, odt_file_names, outputconvert, working_directory)
    #tex_files.extend([join('convert', odt_file_name+'.tex') for odt_file_name in odt_file_names])#list all the newly converted latex files, there is no more odt files to consider at this step
    concatenate(odt_file_names, tex_files, output)#tex_files and txt_files are absolute filepath lists

def concat_others(working_directory):
    output = join(working_directory, 'pages', 'convertconcat')
    other_files = set()
    for f in  next(walk(working_directory))[2]:#file_list is a list of NON-absolute path to original files in working dir
        filename, file_extension = splitext(f)
        if file_extension != '.odt' and file_extension != '.tex':
            other_files.add(f)
    concatenate2(other_files, output)
