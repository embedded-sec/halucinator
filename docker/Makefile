version=1.0

build:
	docker image build -t halucinator_img:${version} --build-arg VERSION=${version} .

run: build
	docker run -it --name halucinator halucinator_img:${version} /bin/bash

bash:
	docker exec -it halucinator /bin/bash

clean:
	docker rm -f halucinator
	docker image rm halucinator_img:${version}
