.PHONY: compile python native demo clean

compile: python native

python:
	python -m compileall -q verityflow

native:
	dotnet build runtime/VerityFlow.Runtime.csproj -c Release --nologo

demo:
	python -m verityflow --help

clean:
	@echo Cleaning generated report artifacts

