package com.malgcheong.orchestra;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@Controller
public class OrchestraController {

    private final OrchestraRepository repo;

    public OrchestraController(OrchestraRepository repo) {
        this.repo = repo;
    }

    @GetMapping({"/", "/orchestra"})
    public String orchestra(Model model) {
        model.addAttribute("overview", repo.overview());
        model.addAttribute("runs", repo.runs());
        model.addAttribute("modelStats", repo.modelStats());
        return "orchestra";
    }

    @GetMapping("/run/{id}")
    public String run(@PathVariable long id, Model model) {
        model.addAttribute("runId", id);
        model.addAttribute("steps", repo.steps(id));
        return "run";
    }
}
